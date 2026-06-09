package com.kakao.backend.commercialarea.service;

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
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.Normalizer;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CommercialAreaService {

    private final StoreRepository storeRepository;
    private final CommercialAreaMetricRepository metricRepository;
    private final StoreNormalizer storeNormalizer;

    public CommercialAreaService(
            StoreRepository storeRepository,
            CommercialAreaMetricRepository metricRepository,
            StoreNormalizer storeNormalizer
    ) {
        this.storeRepository = storeRepository;
        this.metricRepository = metricRepository;
        this.storeNormalizer = storeNormalizer;
    }

    @Transactional
    public StoreImportResponse importCsv(String filePath, String region) {
        if (filePath == null || filePath.isBlank()) {
            int imported = importDemoStores();
            return new StoreImportResponse(imported, (int) storeRepository.count());
        }
        Path path = Path.of(filePath);
        if (!Files.exists(path)) {
            int imported = importDemoStores();
            return new StoreImportResponse(imported, (int) storeRepository.count());
        }
        if (filePath.toLowerCase().endsWith(".zip")) {
            int imported = importZip(path, region);
            return new StoreImportResponse(imported, (int) storeRepository.count());
        }

        int imported = 0;
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            imported = importCsvReader(reader);
        } catch (IOException ignored) {
            imported += importDemoStores();
        }
        return new StoreImportResponse(imported, (int) storeRepository.count());
    }

    private int importZip(Path path, String region) {
        String targetRegion = notBlank(region) ? normalizeSido(region) : "서울";
        try (ZipInputStream zipInputStream = new ZipInputStream(Files.newInputStream(path), StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zipInputStream.getNextEntry()) != null) {
                String entryName = entry.getName();
                if (!entry.isDirectory()
                        && entryName.endsWith(".csv")
                        && normalizeSido(entryName).contains(targetRegion)) {
                    return importCsvReader(new BufferedReader(new InputStreamReader(zipInputStream, StandardCharsets.UTF_8)));
                }
            }
        } catch (IOException ignored) {
            return importDemoStores();
        }
        return importDemoStores();
    }

    private int importCsvReader(BufferedReader reader) throws IOException {
        String headerLine = reader.readLine();
        if (headerLine == null) {
            return 0;
        }
        List<String> headers = parseCsvLine(headerLine).stream()
                .map(header -> header.replace("\uFEFF", "").replace("\"", "").trim())
                .toList();
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
    public int importDemoStores() {
        List<Map<String, String>> rows = new ArrayList<>();
        rows.add(demoRow("demo-001", "연남브루잉", "음식점업", "커피점/카페", "카페", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-002", "연남라떼", "음식점업", "커피점/카페", "카페", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-003", "홍대입구 커피", "음식점업", "커피점/카페", "카페", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-004", "골목 에스프레소", "음식점업", "커피점/카페", "카페", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-005", "연남 베이커리카페", "음식점업", "커피점/카페", "카페", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-006", "연남 디저트", "음식점업", "제과제빵떡케익", "디저트", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-007", "연남 분식", "음식점업", "분식", "분식", "서울", "마포구", "연남동"));
        rows.add(demoRow("demo-008", "상수 카페", "음식점업", "커피점/카페", "카페", "서울", "마포구", "상수동"));
        int count = 0;
        for (Map<String, String> row : rows) {
            upsertStore(storeNormalizer.normalizeCsvRow(row));
            count++;
        }
        return count;
    }

    @Transactional
    public CommercialAreaResponse analyze(CommercialAreaRequest request) {
        if (storeRepository.count() == 0) {
            importDemoStores();
        }
        List<Store> stores = storesForArea(request);
        int totalStores = stores.size();
        int directCompetitors = (int) stores.stream().filter(store -> isDirectCompetitor(store, request)).count();
        int similarCompetitors = (int) stores.stream()
                .filter(store -> !isDirectCompetitor(store, request))
                .filter(store -> isSimilarCompetitor(store, request))
                .count();
        String level = competitionLevel(directCompetitors);
        upsertMetric(request, totalStores, directCompetitors);
        return new CommercialAreaResponse(
                areaLabel(request),
                industryLabel(request),
                totalStores,
                directCompetitors,
                similarCompetitors,
                level,
                List.of(
                        "V0는 소상공인 상가 CSV/샘플 데이터 기준의 단순 경쟁점 계산입니다.",
                        "정확한 임대료/매출/유동인구는 별도 데이터가 필요합니다."
                )
        );
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
            return storeRepository.findBySidoAndSigunguAndDong(sido, request.sigungu(), request.dong());
        }
        if (notBlank(sido) && notBlank(request.sigungu())) {
            return storeRepository.findBySidoAndSigungu(sido, request.sigungu());
        }
        if (notBlank(sido)) {
            return storeRepository.findBySido(sido);
        }
        return storeRepository.findAll();
    }

    private boolean isDirectCompetitor(Store store, CommercialAreaRequest request) {
        return matchesIfPresent(store.getCategoryLarge(), request.industryLarge())
                && matchesIfPresent(store.getCategoryMedium(), request.industryMedium())
                && matchesIfPresent(store.getCategorySmall(), request.industrySmall());
    }

    private boolean isSimilarCompetitor(Store store, CommercialAreaRequest request) {
        return matchesIfPresent(store.getCategoryLarge(), request.industryLarge())
                || matchesIfPresent(store.getCategoryMedium(), request.industryMedium());
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

    private Map<String, String> demoRow(
            String id,
            String name,
            String large,
            String medium,
            String small,
            String sido,
            String sigungu,
            String dong
    ) {
        Map<String, String> row = new LinkedHashMap<>();
        row.put("상가업소번호", id);
        row.put("상호명", name);
        row.put("상권업종대분류명", large);
        row.put("상권업종중분류명", medium);
        row.put("상권업종소분류명", small);
        row.put("표준산업분류코드", "I56220");
        row.put("표준산업분류명", "비알코올 음료점업");
        row.put("시도명", sido);
        row.put("시군구명", sigungu);
        row.put("행정동명", dong);
        row.put("도로명주소", sido + " " + sigungu + " " + dong);
        row.put("지번주소", sido + " " + sigungu + " " + dong);
        row.put("경도", "126.923");
        row.put("위도", "37.562");
        return row;
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
        return String.join(" ", java.util.stream.Stream.of(normalizeSido(request.sido()), request.sigungu(), request.dong())
                .filter(this::notBlank)
                .toList());
    }

    private String industryLabel(CommercialAreaRequest request) {
        return String.join(" / ", java.util.stream.Stream.of(request.industryLarge(), request.industryMedium(), request.industrySmall())
                .filter(this::notBlank)
                .toList());
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
}
