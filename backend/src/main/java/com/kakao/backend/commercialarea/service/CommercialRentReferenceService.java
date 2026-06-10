package com.kakao.backend.commercialarea.service;

import com.kakao.backend.commercialarea.domain.CommercialRentReference;
import com.kakao.backend.commercialarea.dto.RentEstimateResponse;
import com.kakao.backend.commercialarea.dto.RentReferenceImportResponse;
import com.kakao.backend.commercialarea.repository.CommercialRentReferenceRepository;
import java.io.BufferedReader;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CommercialRentReferenceService {

    private static final String DEFAULT_COMMERCIAL_TYPE = "소규모상가";
    private static final String DEFAULT_SOURCE = "부동산통계정보 임대동향 지역별 임대료";
    private static final double DEFAULT_AREA_M2 = 66.0;
    private static final Pattern QUARTER_PATTERN = Pattern.compile("(\\d{4})년\\s*(\\d)분기");
    private static final List<Charset> CSV_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("MS949"),
            Charset.forName("EUC-KR")
    );

    private final CommercialRentReferenceRepository rentReferenceRepository;

    public CommercialRentReferenceService(CommercialRentReferenceRepository rentReferenceRepository) {
        this.rentReferenceRepository = rentReferenceRepository;
    }

    @Transactional
    public RentReferenceImportResponse importCsv(String filePath, String commercialType, String source) {
        String type = defaultIfBlank(commercialType, DEFAULT_COMMERCIAL_TYPE);
        String sourceName = defaultIfBlank(source, DEFAULT_SOURCE);
        Path path = Path.of(filePath);

        RuntimeException lastException = null;
        for (Charset charset : CSV_CHARSETS) {
            try {
                return importCsv(path, charset, type, sourceName);
            } catch (IOException | RuntimeException exception) {
                lastException = new IllegalArgumentException(
                        "임대료 CSV를 " + charset.displayName() + " 인코딩으로 읽지 못했습니다: " + exception.getMessage(),
                        exception
                );
            }
        }
        throw lastException == null ? new IllegalArgumentException("임대료 CSV를 읽지 못했습니다.") : lastException;
    }

    private RentReferenceImportResponse importCsv(Path path, Charset charset, String commercialType, String source) throws IOException {
        try (BufferedReader reader = Files.newBufferedReader(path, charset)) {
            List<String> periodHeaders = parseCsvLine(reader.readLine());
            reader.readLine();
            reader.readLine();

            int periodIndex = findLatestPeriodIndex(periodHeaders);
            Period period = parsePeriod(periodHeaders.get(periodIndex));

            rentReferenceRepository.deleteByCommercialType(commercialType);

            int imported = 0;
            String line;
            while ((line = reader.readLine()) != null) {
                List<String> values = parseCsvLine(line);
                if (values.size() <= periodIndex) {
                    continue;
                }
                BigDecimal rent = parseDecimal(values.get(periodIndex));
                if (rent == null) {
                    continue;
                }

                CommercialRentReference reference = CommercialRentReference.create();
                reference.setSido(clean(values, 1));
                reference.setRegionDepth2(clean(values, 2));
                reference.setRegionDepth3(clean(values, 3));
                reference.setCommercialType(commercialType);
                reference.setBaseYear(period.year());
                reference.setBaseQuarter(period.quarter());
                reference.setRentPerM2Thousand(rent);
                reference.setSource(source);
                rentReferenceRepository.save(reference);
                imported++;
            }

            return new RentReferenceImportResponse(imported, period.year(), period.quarter(), commercialType);
        }
    }

    @Transactional(readOnly = true)
    public RentEstimateResponse estimate(
            String sido,
            String sigungu,
            String dong,
            String address,
            Double areaM2,
            String commercialType
    ) {
        String type = defaultIfBlank(commercialType, DEFAULT_COMMERCIAL_TYPE);
        CommercialRentReference latest = rentReferenceRepository.findTopByCommercialTypeOrderByBaseYearDescBaseQuarterDesc(type)
                .orElseThrow(() -> new IllegalStateException("임대료 기준 데이터가 없습니다. CSV를 먼저 import 해주세요."));

        List<CommercialRentReference> references = rentReferenceRepository.findByCommercialTypeAndBaseYearAndBaseQuarter(
                type,
                latest.getBaseYear(),
                latest.getBaseQuarter()
        );

        CommercialRentReference matched = references.stream()
                .map(reference -> new RentMatch(reference, score(reference, sido, sigungu, dong, address)))
                .filter(match -> match.score() > 0)
                .max(Comparator.comparingInt(RentMatch::score))
                .map(RentMatch::reference)
                .orElse(latest);

        double normalizedArea = areaM2 == null || areaM2 <= 0 ? DEFAULT_AREA_M2 : areaM2;
        int estimatedMonthlyRent = matched.getRentPerM2Thousand()
                .multiply(BigDecimal.valueOf(1000))
                .multiply(BigDecimal.valueOf(normalizedArea))
                .setScale(0, RoundingMode.HALF_UP)
                .intValue();

        return new RentEstimateResponse(
                matched.getSido(),
                matched.getRegionDepth2(),
                matched.getRegionDepth3(),
                matched.getCommercialType(),
                matched.getBaseYear(),
                matched.getBaseQuarter(),
                matched.getRentPerM2Thousand(),
                normalizedArea,
                estimatedMonthlyRent,
                matchLevel(matched, sido),
                matched.getSource()
        );
    }

    private int score(CommercialRentReference reference, String sido, String sigungu, String dong, String address) {
        String haystack = normalize(String.join(" ", List.of(
                defaultIfBlank(address, ""),
                defaultIfBlank(sido, ""),
                defaultIfBlank(sigungu, ""),
                defaultIfBlank(dong, "")
        )));
        String targetSido = normalizeSido(sido);
        String referenceSido = normalizeSido(reference.getSido());

        if ("전국".equals(referenceSido)) {
            return 1;
        }
        if (!referenceSido.equals(targetSido)) {
            return 0;
        }

        String depth3 = normalize(reference.getRegionDepth3());
        String depth2 = normalize(reference.getRegionDepth2());

        if (notBlank(depth3) && !depth3.equals(referenceSido) && haystack.contains(depth3)) {
            return 40;
        }
        if (notBlank(depth2) && !depth2.equals(referenceSido) && haystack.contains(depth2)) {
            return 30;
        }
        return 20;
    }

    private String matchLevel(CommercialRentReference reference, String requestedSido) {
        String referenceSido = normalizeSido(reference.getSido());
        if ("전국".equals(referenceSido)) {
            return "NATIONAL_AVERAGE";
        }
        if (referenceSido.equals(normalizeSido(requestedSido))
                && !normalize(reference.getRegionDepth3()).equals(referenceSido)) {
            return "AREA_AVERAGE";
        }
        return "SIDO_AVERAGE";
    }

    private int findLatestPeriodIndex(List<String> headers) {
        for (int i = headers.size() - 1; i >= 0; i--) {
            if (QUARTER_PATTERN.matcher(headers.get(i)).find()) {
                return i;
            }
        }
        throw new IllegalArgumentException("분기 컬럼을 찾지 못했습니다.");
    }

    private Period parsePeriod(String value) {
        Matcher matcher = QUARTER_PATTERN.matcher(value);
        if (!matcher.find()) {
            throw new IllegalArgumentException("분기 값을 읽지 못했습니다: " + value);
        }
        return new Period(Integer.parseInt(matcher.group(1)), Integer.parseInt(matcher.group(2)));
    }

    private List<String> parseCsvLine(String line) {
        List<String> values = new ArrayList<>();
        if (line == null) {
            return values;
        }
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

    private BigDecimal parseDecimal(String value) {
        if (!notBlank(value)) {
            return null;
        }
        try {
            return new BigDecimal(value.replace(",", "").trim());
        } catch (NumberFormatException exception) {
            return null;
        }
    }

    private String clean(List<String> values, int index) {
        if (index >= values.size()) {
            return "";
        }
        return normalize(values.get(index).replace("\uFEFF", "").replace("\"", ""));
    }

    private String normalizeSido(String value) {
        String normalized = normalize(value);
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

    private String normalize(String value) {
        if (value == null) {
            return "";
        }
        return Normalizer.normalize(value.trim(), Normalizer.Form.NFC);
    }

    private String defaultIfBlank(String value, String fallback) {
        return notBlank(value) ? value.trim() : fallback;
    }

    private boolean notBlank(String value) {
        return value != null && !value.isBlank();
    }

    private record Period(int year, int quarter) {
    }

    private record RentMatch(CommercialRentReference reference, int score) {
    }
}
