package com.kakao.backend.commercialarea.service;

import com.kakao.backend.commercialarea.connector.CommercialStoreApiConnector;
import com.kakao.backend.commercialarea.domain.CommercialAreaMetric;
import com.kakao.backend.commercialarea.domain.Store;
import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.dto.StoreImportResponse;
import com.kakao.backend.commercialarea.normalize.StoreNormalizer;
import com.kakao.backend.commercialarea.repository.CommercialAreaMetricRepository;
import com.kakao.backend.commercialarea.repository.StoreRepository;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.Normalizer;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipFile;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CommercialAreaService {

    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );
    private static final int CSV_BROAD_RESULT_LIMIT = 5_000;

    private final StoreRepository storeRepository;
    private final CommercialAreaMetricRepository metricRepository;
    private final StoreNormalizer storeNormalizer;
    private final CommercialStoreApiConnector storeApiConnector;
    private final String csvFallbackPath;

    public CommercialAreaService(
            StoreRepository storeRepository,
            CommercialAreaMetricRepository metricRepository,
            StoreNormalizer storeNormalizer,
            CommercialStoreApiConnector storeApiConnector,
            @Value("${STARTMATE_COMMERCIAL_AREA_CSV_PATH:}") String csvFallbackPath
    ) {
        this.storeRepository = storeRepository;
        this.metricRepository = metricRepository;
        this.storeNormalizer = storeNormalizer;
        this.storeApiConnector = storeApiConnector;
        this.csvFallbackPath = csvFallbackPath;
    }

    @Transactional
    public StoreImportResponse importCsv(String filePath, String region) {
        String targetPath = notBlank(filePath) ? filePath : csvFallbackPath;
        if (!notBlank(targetPath)) {
            return new StoreImportResponse(0, (int) storeRepository.count());
        }
        Path path = Path.of(targetPath);
        if (!Files.exists(path)) {
            return new StoreImportResponse(0, (int) storeRepository.count());
        }
        if (targetPath.toLowerCase().endsWith(".zip")) {
            int imported = importZip(path, region);
            return new StoreImportResponse(imported, (int) storeRepository.count());
        }

        int imported = importCsvFile(path);
        return new StoreImportResponse(imported, (int) storeRepository.count());
    }

    private int importZip(Path path, String region) {
        String targetRegion = notBlank(region) ? normalizeSido(region) : null;
        for (Charset charset : CSV_CHARSETS) {
            int imported = 0;
            try (ZipInputStream zipInputStream = new ZipInputStream(Files.newInputStream(path), charset)) {
                ZipEntry entry;
                while ((entry = zipInputStream.getNextEntry()) != null) {
                    String entryName = entry.getName();
                    if (!entry.isDirectory()
                            && entryName.endsWith(".csv")
                            && (targetRegion == null || normalizeSido(entryName).contains(targetRegion))) {
                        imported += importCsvReader(new BufferedReader(new InputStreamReader(zipInputStream, charset)));
                        if (targetRegion != null && imported > 0) {
                            return imported;
                        }
                    }
                }
            } catch (IOException ignored) {
                // Try the next charset before giving up on this CSV archive.
            }
            if (imported > 0) {
                return imported;
            }
        }
        return 0;
    }

    private int importCsvFile(Path path) {
        for (Charset charset : CSV_CHARSETS) {
            try (BufferedReader reader = Files.newBufferedReader(path, charset)) {
                int imported = importCsvReader(reader);
                if (imported > 0) {
                    return imported;
                }
            } catch (IOException ignored) {
                // Try the next charset before giving up on this CSV file.
            }
        }
        return 0;
    }

    private int importCsvReader(BufferedReader reader) throws IOException {
        String headerLine = reader.readLine();
        if (headerLine == null) {
            return 0;
        }
        List<String> headers = parseCsvLine(headerLine).stream()
                .map(header -> header.replace("\uFEFF", "").replace("\"", "").trim())
                .toList();
        if (!hasStoreHeaders(headers)) {
            return 0;
        }
        int imported = 0;
        String line;
        while ((line = reader.readLine()) != null) {
            List<String> values = parseCsvLine(line);
            Map<String, String> row = new LinkedHashMap<>();
            for (int i = 0; i < headers.size(); i++) {
                row.put(headers.get(i), i < values.size() ? values.get(i) : "");
            }
            upsertStore(storeNormalizer.normalizeCsvRow(row));
            imported++;
        }
        return imported;
    }

    @Transactional
    public CommercialAreaResponse analyze(CommercialAreaRequest request) {
        List<String> notes = new ArrayList<>();
        List<Store> stores = storesFromApi(request);
        if (!stores.isEmpty()) {
            notes.add("외부 상권 API 데이터를 조회해 최신 주변 점포 기준으로 계산했습니다.");
        } else {
            stores = storesFromLocalData(request, notes);
        }
        int totalStores = stores.size();
        int directCompetitors = (int) stores.stream().filter(store -> isDirectCompetitor(store, request)).count();
        int similarCompetitors = (int) stores.stream()
                .filter(store -> !isDirectCompetitor(store, request))
                .filter(store -> isSimilarCompetitor(store, request))
                .count();
        String level = stores.isEmpty() || !hasIndustryCriteria(request) ? "unknown" : competitionLevel(directCompetitors);
        if (!stores.isEmpty()) {
            upsertMetric(request, totalStores, directCompetitors);
        }
        if (stores.isEmpty()) {
            notes.add("해당 지역/업종 데이터가 없어 경쟁 강도는 보수적으로 해석해야 합니다.");
        }
        if (!hasIndustryCriteria(request)) {
            notes.add("업종 조건이 없어 직접 경쟁점 수는 산출하지 않고 전체 점포 수만 참고했습니다.");
        }
        notes.add("정확한 임대료/매출/유동인구는 별도 데이터가 필요합니다.");
        return new CommercialAreaResponse(
                areaLabel(request),
                industryLabel(request),
                totalStores,
                directCompetitors,
                similarCompetitors,
                level,
                notes
        );
    }

    private List<Store> storesFromLocalData(CommercialAreaRequest request, List<String> notes) {
        List<Store> stores = storesForArea(request);
        if (stores.isEmpty()) {
            stores = storesFromCsvFallback(request, notes);
        }
        if (stores.isEmpty()) {
            stores = broadenStoresForArea(request, notes);
        }
        String sourceNote = sourceNote(stores);
        if (!hasEquivalentSourceNote(stores, notes, sourceNote)) {
            notes.add(sourceNote);
        }
        return stores;
    }

    private boolean hasEquivalentSourceNote(List<Store> stores, List<String> notes, String sourceNote) {
        if (notes.contains(sourceNote)) {
            return true;
        }
        return stores.stream().anyMatch(store -> "sbiz_csv".equals(store.getSource()))
                && notes.stream().anyMatch(note -> note.contains("소상공인 상가 CSV"));
    }

    private List<Store> broadenStoresForArea(CommercialAreaRequest request, List<String> notes) {
        String sido = normalizeSido(request.sido());
        if (notBlank(sido) && notBlank(request.sigungu()) && notBlank(request.dong())) {
            List<Store> sigunguStores = realStores(storeRepository.findBySidoAndSigungu(sido, request.sigungu()));
            if (!sigunguStores.isEmpty()) {
                notes.add("요청한 동 단위 데이터가 없어 같은 시군구 전체 점포 데이터로 확장해 계산했습니다.");
                return sigunguStores;
            }
        }
        if (notBlank(sido) && notBlank(request.sigungu())) {
            List<Store> sidoStores = realStores(storeRepository.findBySido(sido));
            if (!sidoStores.isEmpty()) {
                notes.add("요청한 시군구 데이터가 없어 같은 시도 전체 점포 데이터로 확장해 계산했습니다.");
                return sidoStores;
            }
        }
        List<Store> allStores = realStores(storeRepository.findAll());
        if (!allStores.isEmpty()) {
            notes.add("요청 지역과 일치하는 데이터가 없어 현재 적재된 전체 상가 데이터로 참고 계산했습니다.");
            return allStores;
        }
        return List.of();
    }

    private List<Store> storesFromCsvFallback(CommercialAreaRequest request, List<String> notes) {
        if (!notBlank(csvFallbackPath)) {
            return List.of();
        }
        Path path = Path.of(csvFallbackPath);
        if (!Files.exists(path)) {
            return List.of();
        }

        CsvAreaMatches matches = csvFallbackPath.toLowerCase().endsWith(".zip")
                ? scanCsvZipForArea(path, request)
                : scanCsvFileForArea(path, request);
        List<Store> selected = selectCsvMatches(matches, request, notes);
        if (!selected.isEmpty()) {
            notes.add("외부 상권 API를 사용할 수 없어 소상공인 상가 CSV 데이터를 실시간으로 조회했습니다.");
        }
        return selected;
    }

    private CsvAreaMatches scanCsvZipForArea(Path path, CommercialAreaRequest request) {
        CsvAreaMatches narrowMatches = scanCsvZipForArea(path, request, false);
        if (narrowMatches.hasAny() || !notBlank(request.sigungu())) {
            return narrowMatches;
        }
        return scanCsvZipForArea(path, request, true);
    }

    private CsvAreaMatches scanCsvZipForArea(Path path, CommercialAreaRequest request, boolean sidoFallbackOnly) {
        String targetRegion = normalizeSido(request.sido());
        for (Charset charset : CSV_CHARSETS) {
            CsvAreaMatches matches = new CsvAreaMatches();
            try (ZipFile zipFile = new ZipFile(path.toFile(), charset)) {
                Enumeration<? extends ZipEntry> entries = zipFile.entries();
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    String entryName = entry.getName();
                    if (!entry.isDirectory()
                            && entryName.endsWith(".csv")
                            && (!notBlank(targetRegion) || normalizeSido(entryName).contains(targetRegion))) {
                        try (BufferedReader reader = new BufferedReader(new InputStreamReader(zipFile.getInputStream(entry), charset))) {
                            scanCsvReaderForArea(reader, request, matches, sidoFallbackOnly);
                        }
                    }
                }
                if (matches.hasAny()) {
                    return matches;
                }
            } catch (IOException ignored) {
                // Try the next charset before giving up on this CSV archive.
            }
        }
        return new CsvAreaMatches();
    }

    private CsvAreaMatches scanCsvFileForArea(Path path, CommercialAreaRequest request) {
        CsvAreaMatches narrowMatches = scanCsvFileForArea(path, request, false);
        if (narrowMatches.hasAny() || !notBlank(request.sigungu())) {
            return narrowMatches;
        }
        return scanCsvFileForArea(path, request, true);
    }

    private CsvAreaMatches scanCsvFileForArea(Path path, CommercialAreaRequest request, boolean sidoFallbackOnly) {
        for (Charset charset : CSV_CHARSETS) {
            CsvAreaMatches matches = new CsvAreaMatches();
            try (BufferedReader reader = Files.newBufferedReader(path, charset)) {
                scanCsvReaderForArea(reader, request, matches, sidoFallbackOnly);
                if (matches.hasAny()) {
                    return matches;
                }
            } catch (IOException ignored) {
                // Try the next charset before giving up on this CSV file.
            }
        }
        return new CsvAreaMatches();
    }

    private void scanCsvReaderForArea(
            BufferedReader reader,
            CommercialAreaRequest request,
            CsvAreaMatches matches,
            boolean sidoFallbackOnly
    ) throws IOException {
        String headerLine = reader.readLine();
        if (headerLine == null) {
            return;
        }
        List<String> headers = parseCsvLine(headerLine).stream()
                .map(header -> header.replace("\uFEFF", "").replace("\"", "").trim())
                .toList();
        if (!hasStoreHeaders(headers)) {
            return;
        }

        CsvHeaderIndexes indexes = csvHeaderIndexes(headers);
        String sido = normalizeSido(request.sido());
        String sigungu = request.sigungu();
        String dong = request.dong();
        String rawSidoNeedle = notBlank(sido) ? sido : null;
        String rawSigunguNeedle = !sidoFallbackOnly && notBlank(sigungu) ? sigungu : null;
        String line;
        while ((line = reader.readLine()) != null) {
            if (!rawLineMayMatch(line, rawSidoNeedle, rawSigunguNeedle)) {
                continue;
            }
            List<String> values = parseCsvLine(line);
            String rowSido = normalizeSido(valueAt(values, indexes.sido()));
            String rowSigungu = valueAt(values, indexes.sigungu());
            String rowDong = valueAt(values, indexes.dong());

            if (notBlank(sido) && !sido.equals(rowSido)) {
                continue;
            }
            boolean addSido = notBlank(sido) && sido.equals(rowSido);
            if (sidoFallbackOnly) {
                if (addSido) {
                    addCsvMatch(matches.sido, csvStoreFromValues(values, indexes), true);
                }
                continue;
            }

            boolean sigunguMatches = !notBlank(sigungu) || sigungu.equals(rowSigungu);
            boolean dongMatches = !notBlank(dong) || dong.equals(rowDong);
            boolean addExact = sigunguMatches && dongMatches;
            boolean addSigungu = notBlank(sigungu) && sigungu.equals(rowSigungu);
            boolean addAll = !notBlank(sido);
            if (!addExact && !addSigungu && !addAll) {
                continue;
            }

            Store store = csvStoreFromValues(values, indexes);
            if (addExact) {
                addCsvMatch(matches.exact, store, shouldLimitExactCsvMatches(request));
            }
            if (addSigungu) {
                addCsvMatch(matches.sigungu, store, false);
            }
            if (addAll) {
                addCsvMatch(matches.all, store, true);
            }
        }
    }

    private boolean rawLineMayMatch(String line, String sidoNeedle, String sigunguNeedle) {
        return (!notBlank(sidoNeedle) || line.contains(sidoNeedle))
                && (!notBlank(sigunguNeedle) || line.contains(sigunguNeedle));
    }

    private int firstHeaderIndex(List<String> headers, String... names) {
        for (String name : names) {
            int index = headers.indexOf(name);
            if (index >= 0) {
                return index;
            }
        }
        return -1;
    }

    private String valueAt(List<String> values, int index) {
        if (index < 0 || index >= values.size()) {
            return null;
        }
        String value = values.get(index);
        return notBlank(value) ? value : null;
    }

    private Map<String, String> toCsvRow(List<String> headers, List<String> values) {
        Map<String, String> row = new LinkedHashMap<>();
        for (int i = 0; i < headers.size(); i++) {
            row.put(headers.get(i), i < values.size() ? values.get(i) : "");
        }
        return row;
    }

    private CsvHeaderIndexes csvHeaderIndexes(List<String> headers) {
        return new CsvHeaderIndexes(
                firstHeaderIndex(headers, "상가업소번호", "상가업소ID", "bizesId", "source_store_id", "id"),
                firstHeaderIndex(headers, "상호명", "store_name", "상가업소명", "bizesNm"),
                firstHeaderIndex(headers, "상권업종대분류명", "category_large", "대분류명", "indsLclsNm"),
                firstHeaderIndex(headers, "상권업종중분류명", "category_medium", "중분류명", "indsMclsNm"),
                firstHeaderIndex(headers, "상권업종소분류명", "category_small", "소분류명", "indsSclsNm"),
                firstHeaderIndex(headers, "표준산업분류코드", "industry_code", "ksicCd"),
                firstHeaderIndex(headers, "표준산업분류명", "industry_name", "ksicNm"),
                firstHeaderIndex(headers, "시도명", "sido", "ctprvnNm"),
                firstHeaderIndex(headers, "시군구명", "sigungu", "signguNm"),
                firstHeaderIndex(headers, "행정동명", "법정동명", "dong", "adongNm", "ldongNm"),
                firstHeaderIndex(headers, "도로명주소", "road_address", "rdnmAdr"),
                firstHeaderIndex(headers, "지번주소", "jibun_address", "lnoAdr"),
                firstHeaderIndex(headers, "경도", "longitude", "lon"),
                firstHeaderIndex(headers, "위도", "latitude", "lat")
        );
    }

    private Store csvStoreFromValues(List<String> values, CsvHeaderIndexes indexes) {
        Store store = Store.create();
        store.setSource("sbiz_csv");
        String storeName = valueAt(values, indexes.storeName());
        String roadAddress = valueAt(values, indexes.roadAddress());
        String jibunAddress = valueAt(values, indexes.jibunAddress());
        String sourceStoreId = valueAt(values, indexes.sourceStoreId());
        store.setSourceStoreId(notBlank(sourceStoreId)
                ? sourceStoreId
                : defaultSourceStoreId(storeName, roadAddress, jibunAddress));
        store.setStoreName(storeName);
        store.setCategoryLarge(valueAt(values, indexes.categoryLarge()));
        store.setCategoryMedium(valueAt(values, indexes.categoryMedium()));
        store.setCategorySmall(valueAt(values, indexes.categorySmall()));
        store.setIndustryCode(valueAt(values, indexes.industryCode()));
        store.setIndustryName(valueAt(values, indexes.industryName()));
        store.setSido(normalizeSido(valueAt(values, indexes.sido())));
        store.setSigungu(valueAt(values, indexes.sigungu()));
        store.setDong(valueAt(values, indexes.dong()));
        store.setRoadAddress(roadAddress);
        store.setJibunAddress(jibunAddress);
        store.setLongitude(parseDouble(valueAt(values, indexes.longitude())));
        store.setLatitude(parseDouble(valueAt(values, indexes.latitude())));
        return store;
    }

    private String defaultSourceStoreId(String storeName, String roadAddress, String jibunAddress) {
        String address = notBlank(roadAddress) ? roadAddress : jibunAddress;
        String basis = blankToEmpty(storeName) + "|" + blankToEmpty(address);
        return "generated-" + Integer.toUnsignedString(basis.hashCode());
    }

    private String blankToEmpty(String value) {
        return value == null ? "" : value;
    }

    private Double parseDouble(String value) {
        if (!notBlank(value)) {
            return null;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private void addCsvMatch(List<Store> stores, Store store, boolean limited) {
        if (!limited || stores.size() < CSV_BROAD_RESULT_LIMIT) {
            stores.add(store);
        }
    }

    private boolean shouldLimitExactCsvMatches(CommercialAreaRequest request) {
        return !notBlank(request.sigungu());
    }

    private List<Store> selectCsvMatches(
            CsvAreaMatches matches,
            CommercialAreaRequest request,
            List<String> notes
    ) {
        if (!matches.exact.isEmpty()) {
            if (shouldLimitExactCsvMatches(request)) {
                notes.add("요청 범위가 넓어 CSV 점포 데이터를 최대 " + CSV_BROAD_RESULT_LIMIT + "건까지 참고했습니다.");
            }
            return matches.exact;
        }
        if (notBlank(request.dong()) && !matches.sigungu.isEmpty()) {
            notes.add("요청한 동 단위 CSV 데이터가 없어 같은 시군구 전체 점포 데이터로 확장해 계산했습니다.");
            return matches.sigungu;
        }
        if (notBlank(request.sigungu()) && !matches.sido.isEmpty()) {
            notes.add("요청한 시군구 CSV 데이터가 없어 같은 시도 점포 데이터로 확장해 계산했습니다.");
            return matches.sido;
        }
        if (!matches.all.isEmpty()) {
            notes.add("요청 지역이 없어 CSV 점포 데이터를 최대 " + CSV_BROAD_RESULT_LIMIT + "건까지 참고했습니다.");
            return matches.all;
        }
        return List.of();
    }

    private List<Store> storesFromApi(CommercialAreaRequest request) {
        List<Map<String, Object>> rows = storeApiConnector.fetchStoresInRadius(request);
        if (rows.isEmpty()) {
            return List.of();
        }
        List<Store> stores = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Store store = storeNormalizer.normalizeApiRow(row);
            if (notBlank(store.getSourceStoreId()) || notBlank(store.getStoreName())) {
                upsertStore(store);
                stores.add(store);
            }
        }
        return stores;
    }

    private void upsertStore(Store incoming) {
        storeRepository.findBySourceAndSourceStoreId(incoming.getSource(), incoming.getSourceStoreId())
                .ifPresentOrElse(existing -> {
                    storeNormalizer.copyInto(incoming, existing);
                    storeRepository.save(existing);
                }, () -> storeRepository.save(incoming));
    }

    private List<Store> storesForArea(CommercialAreaRequest request) {
        String sido = normalizeSido(request.sido());
        if (notBlank(sido) && notBlank(request.sigungu()) && notBlank(request.dong())) {
            return realStores(storeRepository.findBySidoAndSigunguAndDong(sido, request.sigungu(), request.dong()));
        }
        if (notBlank(sido) && notBlank(request.sigungu())) {
            return realStores(storeRepository.findBySidoAndSigungu(sido, request.sigungu()));
        }
        if (notBlank(sido)) {
            return realStores(storeRepository.findBySido(sido));
        }
        return realStores(storeRepository.findAll());
    }

    private List<Store> realStores(List<Store> stores) {
        return stores.stream()
                .filter(store -> !"demo".equals(store.getSource()))
                .toList();
    }

    private boolean isDirectCompetitor(Store store, CommercialAreaRequest request) {
        if (!hasIndustryCriteria(request)) {
            return false;
        }
        boolean largeMatches = !notBlank(request.industryLarge())
                || matchesAnyCategory(store, request.industryLarge());
        if (!largeMatches) {
            return false;
        }
        if (notBlank(request.industrySmall())) {
            return matchesAnyCategory(store, request.industrySmall());
        }
        if (notBlank(request.industryMedium())) {
            return matchesAnyCategory(store, request.industryMedium());
        }
        return true;
    }

    private boolean isSimilarCompetitor(Store store, CommercialAreaRequest request) {
        if (!hasIndustryCriteria(request)) {
            return false;
        }
        return matchesAnyCategory(store, request.industryLarge())
                || matchesAnyCategory(store, request.industryMedium());
    }

    private boolean hasIndustryCriteria(CommercialAreaRequest request) {
        return notBlank(request.industryLarge())
                || notBlank(request.industryMedium())
                || notBlank(request.industrySmall());
    }

    private boolean matchesIfPresent(String actual, String expected) {
        if (!notBlank(expected)) {
            return true;
        }
        if (!notBlank(actual)) {
            return false;
        }
        return actual.contains(expected) || expected.contains(actual);
    }

    private boolean matchesAnyCategory(Store store, String expected) {
        if (!notBlank(expected)) {
            return false;
        }
        return matchesIfPresent(store.getCategoryLarge(), expected)
                || matchesIfPresent(store.getCategoryMedium(), expected)
                || matchesIfPresent(store.getCategorySmall(), expected)
                || matchesIfPresent(store.getIndustryName(), expected);
    }

    private boolean hasStoreHeaders(List<String> headers) {
        return headers.contains("상호명")
                || headers.contains("상가업소명")
                || headers.contains("bizesNm")
                || headers.contains("상가업소번호");
    }

    private String sourceNote(List<Store> stores) {
        if (stores.stream().anyMatch(store -> "sbiz_api".equals(store.getSource()))) {
            return "DB에 저장된 외부 상권 API 스냅샷을 사용했습니다.";
        }
        if (stores.stream().anyMatch(store -> "sbiz_csv".equals(store.getSource()))) {
            return "외부 상권 API를 사용할 수 없어 소상공인 상가 CSV 데이터를 사용했습니다.";
        }
        if (stores.isEmpty()) {
            return "외부 상권 API와 CSV에서 사용할 수 있는 점포 데이터를 찾지 못했습니다.";
        }
        return "DB에 저장된 실제 상가 데이터를 사용했습니다.";
    }

    private String competitionLevel(int directCompetitors) {
        if (directCompetitors <= 5) {
            return "low";
        }
        if (directCompetitors <= 20) {
            return "medium";
        }
        return "high";
    }

    private void upsertMetric(CommercialAreaRequest request, int totalStores, int directCompetitors) {
        CommercialAreaMetric metric = metricRepository
                .findBySidoAndSigunguAndDongAndIndustryLargeAndIndustryMediumAndIndustrySmall(
                        normalizeSido(request.sido()),
                        request.sigungu(),
                        request.dong(),
                        request.industryLarge(),
                        request.industryMedium(),
                        request.industrySmall()
                )
                .orElseGet(CommercialAreaMetric::create);
        metric.setSido(normalizeSido(request.sido()));
        metric.setSigungu(request.sigungu());
        metric.setDong(request.dong());
        metric.setIndustryLarge(request.industryLarge());
        metric.setIndustryMedium(request.industryMedium());
        metric.setIndustrySmall(request.industrySmall());
        metric.setStoreCount(totalStores);
        metric.setCompetitorCount(directCompetitors);
        metric.setCalculatedAt(LocalDateTime.now());
        metricRepository.save(metric);
    }

    private List<String> parseCsvLine(String line) {
        List<String> values = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (ch == '"') {
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else {
                    quoted = !quoted;
                }
            } else if (ch == ',' && !quoted) {
                values.add(current.toString().trim());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }
        values.add(current.toString().trim());
        return values;
    }

    private String areaLabel(CommercialAreaRequest request) {
        String label = String.join(" ", java.util.stream.Stream.of(normalizeSido(request.sido()), request.sigungu(), request.dong())
                .filter(this::notBlank)
                .toList());
        return notBlank(label) ? label : "전체 적재 데이터";
    }

    private String industryLabel(CommercialAreaRequest request) {
        String label = String.join(" / ", java.util.stream.Stream.of(request.industryLarge(), request.industryMedium(), request.industrySmall())
                .filter(this::notBlank)
                .toList());
        return notBlank(label) ? label : "선택 업종 없음";
    }

    private boolean notBlank(String value) {
        return value != null && !value.isBlank();
    }

    private String normalizeSido(String value) {
        if (value == null || value.isBlank()) {
            return value;
        }
        String normalized = Normalizer.normalize(value.trim(), Normalizer.Form.NFC);
        return switch (normalized) {
            case "서울특별시" -> "서울";
            case "부산광역시" -> "부산";
            case "대구광역시" -> "대구";
            case "인천광역시" -> "인천";
            case "광주광역시" -> "광주";
            case "대전광역시" -> "대전";
            case "울산광역시" -> "울산";
            case "세종특별자치시" -> "세종";
            case "경기도" -> "경기";
            case "강원특별자치도", "강원도" -> "강원";
            case "충청북도" -> "충북";
            case "충청남도" -> "충남";
            case "전북특별자치도", "전라북도" -> "전북";
            case "전라남도" -> "전남";
            case "경상북도" -> "경북";
            case "경상남도" -> "경남";
            case "제주특별자치도" -> "제주";
            default -> normalized;
        };
    }

    private static final class CsvAreaMatches {

        private final List<Store> exact = new ArrayList<>();
        private final List<Store> sigungu = new ArrayList<>();
        private final List<Store> sido = new ArrayList<>();
        private final List<Store> all = new ArrayList<>();

        private boolean hasAny() {
            return !exact.isEmpty() || !sigungu.isEmpty() || !sido.isEmpty() || !all.isEmpty();
        }
    }

    private record CsvHeaderIndexes(
            int sourceStoreId,
            int storeName,
            int categoryLarge,
            int categoryMedium,
            int categorySmall,
            int industryCode,
            int industryName,
            int sido,
            int sigungu,
            int dong,
            int roadAddress,
            int jibunAddress,
            int longitude,
            int latitude
    ) {
    }
}
