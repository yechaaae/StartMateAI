package com.kakao.backend.policy.normalize;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.policy.domain.SupportProgram;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class SupportProgramNormalizer {

    private static final Pattern BRACKETED_TEXT = Pattern.compile("[\\[【(（]\\s*([^\\]】)）]{1,30})\\s*[\\]】)）]");
    private static final List<RegionAlias> REGION_ALIASES = List.of(
            new RegionAlias("서울", List.of("서울", "서울시", "서울특별시")),
            new RegionAlias("부산", List.of("부산", "부산시", "부산광역시")),
            new RegionAlias("대구", List.of("대구", "대구시", "대구광역시")),
            new RegionAlias("인천", List.of("인천", "인천시", "인천광역시")),
            new RegionAlias("광주", List.of("광주", "광주시", "광주광역시")),
            new RegionAlias("대전", List.of("대전", "대전시", "대전광역시")),
            new RegionAlias("울산", List.of("울산", "울산시", "울산광역시")),
            new RegionAlias("세종", List.of("세종", "세종시", "세종특별자치시")),
            new RegionAlias("경기", List.of("경기", "경기도")),
            new RegionAlias("강원", List.of("강원", "강원도", "강원특별자치도")),
            new RegionAlias("충북", List.of("충북", "충청북도")),
            new RegionAlias("충남", List.of("충남", "충청남도")),
            new RegionAlias("전북", List.of("전북", "전라북도", "전북특별자치도")),
            new RegionAlias("전남", List.of("전남", "전라남도")),
            new RegionAlias("경북", List.of("경북", "경상북도")),
            new RegionAlias("경남", List.of("경남", "경상남도")),
            new RegionAlias("제주", List.of("제주", "제주도", "제주특별자치도"))
    );

    private final ObjectMapper objectMapper;
    private final DateNormalizer dateNormalizer;

    public SupportProgramNormalizer(ObjectMapper objectMapper, DateNormalizer dateNormalizer) {
        this.objectMapper = objectMapper;
        this.dateNormalizer = dateNormalizer;
    }

    public SupportProgram normalize(String source, Map<String, Object> raw) {
        SupportProgram program = SupportProgram.create();
        program.setSource(source);
        program.setSourceId(defaultSourceId(source, raw));
        program.setTitle(defaultString(first(raw,
                "bizPbancNm", "biz_pbanc_nm", "pblancNm", "pbancNm", "title", "plcyNm", "polyBizSjnm", "사업명", "공고명"
        ), "제목 미상 지원사업"));
        program.setSummary(first(raw,
                "bizPbancCn", "biz_pbanc_cn", "summary", "plcyExplnCn", "polyItcnCn", "pblancContent", "bsnsSumryCn", "사업개요", "정책설명"
        ));
        program.setContent(first(raw,
                "content", "cn", "detail", "dtlCn", "bizPbancCn", "plcyExplnCn", "polyItcnCn"
        ));
        program.setCategory(first(raw, "suptBizClssCdNm", "bizClsfNm", "category", "plcyKywdNm", "hashtags", "분야"));
        program.setTarget(first(raw, "aplyTrgt", "trgtCn", "sprtTrgtCn", "target", "지원대상", "신청대상"));
        program.setAgeCondition(inferAgeCondition(program.getTarget(), program.getTitle(), first(raw, "ageInfo", "sprtTrgtMinAge", "sprtTrgtMaxAge")));
        program.setBusinessStageCondition(inferStage(program.getTitle(), program.getSummary(), program.getTarget(), first(raw, "startupStage", "창업단계")));
        program.setRegionCondition(resolveRegionCondition(
                first(raw, "region", "areaNm", "plcyRgnNm", "suptRegin", "sido", "지역", "법정시군구코드"),
                inferTitleRegionCondition(program.getTitle()),
                inferRegionCondition(program.getTitle(), program.getSummary(), program.getContent(), program.getTarget(), program.getCategory())
        ));
        program.setIndustryCondition(first(raw, "industry", "industNm", "업종", "지원업종"));
        program.setSupportType(inferSupportType(program.getTitle(), program.getSummary(), program.getCategory()));
        program.setOrganization(first(raw, "sprvInstNm", "intgPbancInsttNm", "operInstNm", "organization", "cnsgNmor", "기관명"));
        program.setDepartment(first(raw, "department", "deptNm", "chargeDeptNm", "부서명"));
        program.setContact(first(raw, "inqireTelno", "inqTelNo", "rprsntvTelno", "contact", "전화문의", "문의처"));
        String period = first(raw, "rqutPrdCn", "aplyPrd", "pbancRcptPrd", "신청기간", "모집기간");
        program.setApplicationStartDate(firstDate(first(raw, "pbancRcptBgngDt", "aplyBgngDt", "startDate", "신청시작일"), period));
        program.setApplicationEndDate(lastDate(first(raw, "pbancRcptEndDt", "aplyEndDt", "endDate", "신청종료일"), period));
        program.setStatus(inferStatus(program.getApplicationStartDate(), program.getApplicationEndDate(), first(raw, "status", "pbancSttsNm", "상태")));
        program.setSupportAmount(first(raw, "sprtAmt", "supportAmount", "지원금액", "지원규모"));
        program.setRequiredDocuments(first(raw, "requiredDocuments", "documents", "sbmsnDcmnt", "제출서류"));
        program.setApplyUrl(first(raw, "aplyUrl", "reqstUrl", "onlineReqstUrl", "신청URL"));
        program.setDetailUrl(first(raw, "dtlUrl", "sourceUrl", "link", "pblancUrl", "url", "상세URL"));
        program.setSourceUrl(firstNonBlank(program.getDetailUrl(), program.getApplyUrl()));
        program.setTags(first(raw, "tags", "hashtags", "keywords", "키워드"));
        program.setRawPayload(toJson(raw));
        return program;
    }

    public void copyInto(SupportProgram source, SupportProgram target) {
        target.setSourceUrl(source.getSourceUrl());
        target.setTitle(source.getTitle());
        target.setSummary(source.getSummary());
        target.setContent(source.getContent());
        target.setCategory(source.getCategory());
        target.setSupportType(source.getSupportType());
        target.setTarget(source.getTarget());
        target.setAgeCondition(source.getAgeCondition());
        target.setBusinessStageCondition(source.getBusinessStageCondition());
        target.setRegionCondition(source.getRegionCondition());
        target.setIndustryCondition(source.getIndustryCondition());
        target.setOrganization(source.getOrganization());
        target.setDepartment(source.getDepartment());
        target.setContact(source.getContact());
        target.setApplicationStartDate(source.getApplicationStartDate());
        target.setApplicationEndDate(source.getApplicationEndDate());
        target.setStatus(source.getStatus());
        target.setSupportAmount(source.getSupportAmount());
        target.setRequiredDocuments(source.getRequiredDocuments());
        target.setApplyUrl(source.getApplyUrl());
        target.setDetailUrl(source.getDetailUrl());
        target.setTags(source.getTags());
        target.setRawPayload(source.getRawPayload());
    }

    private String defaultSourceId(String source, Map<String, Object> raw) {
        String explicit = first(raw,
                "id", "sourceId", "source_id", "pbancSn", "pblancId", "bizPbancSn", "plcyNo", "polyBizSecd", "서비스ID"
        );
        if (explicit != null && !explicit.isBlank()) {
            return explicit;
        }
        String basis = source + "|" + first(raw, "title", "bizPbancNm", "pblancNm", "plcyNm", "polyBizSjnm") + "|"
                + first(raw, "organization", "sprvInstNm", "intgPbancInsttNm", "operInstNm");
        return "generated-" + Integer.toUnsignedString(basis.hashCode());
    }

    private LocalDate firstDate(String primary, String fallback) {
        LocalDate date = dateNormalizer.firstDate(primary);
        return date != null ? date : dateNormalizer.firstDate(fallback);
    }

    private LocalDate lastDate(String primary, String fallback) {
        LocalDate date = dateNormalizer.lastDate(primary);
        return date != null ? date : dateNormalizer.lastDate(fallback);
    }

    private String inferStatus(LocalDate start, LocalDate end, String rawStatus) {
        if (rawStatus != null && !rawStatus.isBlank()) {
            String normalized = rawStatus.toLowerCase(Locale.ROOT);
            if (normalized.contains("마감") || normalized.contains("closed")) {
                return "closed";
            }
            if (normalized.contains("모집") || normalized.contains("open")) {
                return "open";
            }
        }
        LocalDate today = LocalDate.now();
        if (start != null && today.isBefore(start)) {
            return "upcoming";
        }
        if (end != null && today.isAfter(end)) {
            return "closed";
        }
        if (start != null || end != null) {
            return "open";
        }
        return "unknown";
    }

    private String inferAgeCondition(String... values) {
        String text = join(values);
        if (text.contains("청년") || text.matches(".*(만\\s*)?(19|20|29|34|39).*")) {
            return "youth_19_39";
        }
        return null;
    }

    private String inferStage(String... values) {
        String text = join(values);
        if (text.contains("예비")) {
            return "idea,preparing,pre_founder";
        }
        if (text.contains("초기")) {
            return "mvp,pre_revenue,revenue,initial_founder";
        }
        if (text.contains("재창업")) {
            return "re_founder";
        }
        return null;
    }

    private String inferRegionCondition(String... values) {
        String text = join(values);
        if (text.isBlank()) {
            return null;
        }
        if (containsAny(text, "비수도권")) {
            return "비수도권";
        }
        if (containsAny(text, "전국", "전 지역", "전체 지역")) {
            return "전국";
        }

        List<String> bracketMatches = matchedRegions(bracketedText(text), true);
        if (!bracketMatches.isEmpty()) {
            return String.join(",", bracketMatches);
        }

        List<String> matches = matchedRegions(text, false);
        return matches.isEmpty() ? null : String.join(",", matches);
    }

    private String inferTitleRegionCondition(String title) {
        if (title == null || title.isBlank()) {
            return null;
        }
        if (containsAny(title, "비수도권")) {
            return "비수도권";
        }
        List<String> bracketMatches = matchedRegions(bracketedText(title), true);
        if (!bracketMatches.isEmpty()) {
            return String.join(",", bracketMatches);
        }
        List<String> strongMatches = matchedStrongTitleRegions(title);
        return strongMatches.isEmpty() ? null : String.join(",", strongMatches);
    }

    private String resolveRegionCondition(String explicitRegion, String titleRegion, String inferredRegion) {
        if (explicitRegion != null && !explicitRegion.isBlank()) {
            if (containsAny(explicitRegion, "전국", "전체") && titleRegion != null && !titleRegion.isBlank()) {
                return titleRegion;
            }
            return explicitRegion;
        }
        return firstNonBlank(titleRegion, inferredRegion);
    }

    private String bracketedText(String text) {
        Matcher matcher = BRACKETED_TEXT.matcher(text);
        StringBuilder builder = new StringBuilder();
        while (matcher.find()) {
            builder.append(' ').append(matcher.group(1));
        }
        return builder.toString();
    }

    private List<String> matchedRegions(String text, boolean allowShortAlias) {
        List<String> matches = new ArrayList<>();
        for (RegionAlias region : REGION_ALIASES) {
            if (region.matches(text, allowShortAlias) && !matches.contains(region.name())) {
                matches.add(region.name());
            }
        }
        return matches;
    }

    private List<String> matchedStrongTitleRegions(String text) {
        List<String> matches = new ArrayList<>();
        for (RegionAlias region : REGION_ALIASES) {
            if (region.matchesStrongTitle(text) && !matches.contains(region.name())) {
                matches.add(region.name());
            }
        }
        return matches;
    }

    private String inferSupportType(String... values) {
        String text = join(values);
        if (containsAny(text, "대출", "융자")) {
            return "loan";
        }
        if (containsAny(text, "보증")) {
            return "guarantee";
        }
        if (containsAny(text, "교육", "강의", "아카데미")) {
            return "education";
        }
        if (containsAny(text, "멘토", "컨설팅", "상담")) {
            return "mentoring";
        }
        if (containsAny(text, "공간", "입주", "센터", "사무실")) {
            return "space";
        }
        if (containsAny(text, "r&d", "연구", "기술개발")) {
            return "rnd";
        }
        if (containsAny(text, "마케팅", "판로", "홍보", "수출")) {
            return "marketing";
        }
        if (containsAny(text, "자금", "사업화", "지원금", "보조금")) {
            return "grant";
        }
        return "grant";
    }

    private boolean containsAny(String text, String... terms) {
        for (String term : terms) {
            if (text.toLowerCase(Locale.ROOT).contains(term.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }

    private String join(String... values) {
        return String.join(" ", java.util.stream.Stream.of(values)
                .filter(value -> value != null && !value.isBlank())
                .toList());
    }

    @SuppressWarnings("unchecked")
    private String first(Map<String, Object> raw, String... keys) {
        for (String key : keys) {
            Object value = raw.get(key);
            if (value == null) {
                value = raw.get(toSnakeCase(key));
            }
            if (value instanceof Map<?, ?> map && map.containsKey("name")) {
                value = ((Map<String, Object>) map).get("name");
            }
            String text = stringify(value);
            if (text != null && !text.isBlank()) {
                return text.trim();
            }
        }
        return null;
    }

    private String stringify(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Collection<?> collection) {
            return collection.stream().map(String::valueOf).reduce((left, right) -> left + "," + right).orElse(null);
        }
        return String.valueOf(value);
    }

    private String defaultString(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String firstNonBlank(String first, String second) {
        return first != null && !first.isBlank() ? first : second;
    }

    private String toSnakeCase(String value) {
        return value.replaceAll("([a-z])([A-Z])", "$1_$2").toLowerCase(Locale.ROOT);
    }

    private String toJson(Map<String, Object> raw) {
        try {
            return objectMapper.writeValueAsString(raw);
        } catch (JsonProcessingException ignored) {
            return "{}";
        }
    }

    private record RegionAlias(String name, List<String> aliases) {

        private boolean matches(String text, boolean allowShortAlias) {
            if (text == null || text.isBlank()) {
                return false;
            }
            for (String alias : aliases) {
                if ((allowShortAlias || alias.length() > 2) && text.contains(alias)) {
                    return true;
                }
            }
            return false;
        }

        private boolean matchesStrongTitle(String text) {
            if (text == null || text.isBlank()) {
                return false;
            }
            for (String alias : aliases) {
                if (alias.length() > 2 && text.contains(alias)) {
                    return true;
                }
                Pattern pattern = Pattern.compile("(^|[\\s\\[【(（])" + Pattern.quote(alias) + "(?=$|[\\s\\]】)）·ㆍ\\-_/])");
                if (pattern.matcher(text).find()) {
                    return true;
                }
            }
            return false;
        }
    }
}
