package com.kakao.backend.policy.service;

import com.kakao.backend.policy.connector.BizinfoConnector;
import com.kakao.backend.policy.connector.KstartupConnector;
import com.kakao.backend.policy.connector.YouthCenterConnector;
import com.kakao.backend.policy.domain.SupportProgram;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.dto.SupportProgramSyncResponse;
import com.kakao.backend.policy.matcher.SupportProgramMatcher;
import com.kakao.backend.policy.normalize.SupportProgramNormalizer;
import com.kakao.backend.policy.repository.SupportProgramRepository;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SupportProgramService {

    private final SupportProgramRepository supportProgramRepository;
    private final SupportProgramNormalizer normalizer;
    private final SupportProgramMatcher matcher;
    private final KstartupConnector kstartupConnector;
    private final BizinfoConnector bizinfoConnector;
    private final YouthCenterConnector youthCenterConnector;

    public SupportProgramService(
            SupportProgramRepository supportProgramRepository,
            SupportProgramNormalizer normalizer,
            SupportProgramMatcher matcher,
            KstartupConnector kstartupConnector,
            BizinfoConnector bizinfoConnector,
            YouthCenterConnector youthCenterConnector
    ) {
        this.supportProgramRepository = supportProgramRepository;
        this.normalizer = normalizer;
        this.matcher = matcher;
        this.kstartupConnector = kstartupConnector;
        this.bizinfoConnector = bizinfoConnector;
        this.youthCenterConnector = youthCenterConnector;
    }

    @Transactional
    public SupportProgramSyncResponse sync(String source) {
        String normalizedSource = source == null || source.isBlank() ? "all" : source;
        Map<String, Integer> counts = new LinkedHashMap<>();
        if ("all".equals(normalizedSource) || "kstartup".equals(normalizedSource)) {
            counts.put("kstartup", upsertRaw("kstartup", kstartupConnector.fetchKstartupAnnouncements(Map.of())));
        }
        if ("all".equals(normalizedSource) || "bizinfo".equals(normalizedSource)) {
            counts.put("bizinfo", upsertRaw("bizinfo", bizinfoConnector.fetchBizinfoPrograms(Map.of())));
        }
        if ("all".equals(normalizedSource) || "youthcenter".equals(normalizedSource)) {
            counts.put("youthcenter", upsertRaw("youthcenter", youthCenterConnector.fetchYouthPolicies(Map.of())));
        }
        int totalUpserted = counts.values().stream().mapToInt(Integer::intValue).sum();
        if (totalUpserted == 0) {
            counts.put("demo", upsertDemoPrograms());
        }
        return new SupportProgramSyncResponse(counts, (int) supportProgramRepository.count());
    }

    @Transactional(readOnly = true)
    public List<RecommendedProgramResponse> recommend(SupportProgramRecommendationRequest request) {
        List<SupportProgram> programs = supportProgramRepository.findAll();
        if (programs.isEmpty()) {
            throw new IllegalStateException("support_programs is empty. Import seeds first.");
        }
        return programs.stream()
                .map(program -> matcher.match(program, request))
                .sorted(Comparator.comparingInt(RecommendedProgramResponse::matchScore).reversed()
                        .thenComparing(RecommendedProgramResponse::applicationEndDate, Comparator.nullsLast(Comparator.naturalOrder())))
                .limit(10)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> exportForAiIndex() {
        return supportProgramRepository.findAll().stream()
                .map(this::toAiIndexDocument)
                .toList();
    }

    @Transactional
    public List<RecommendedProgramResponse> recommendWithDemoFallback(SupportProgramRecommendationRequest request) {
        if (supportProgramRepository.count() == 0) {
            upsertDemoPrograms();
        }
        return recommend(request);
    }

    @Transactional
    public int upsertDemoPrograms() {
        List<Map<String, Object>> demoPrograms = List.of(
                Map.ofEntries(
                        Map.entry("id", "demo-youth-pre-package"),
                        Map.entry("title", "2026 청년 예비창업 패키지"),
                        Map.entry("summary", "청년 예비창업자의 사업화 자금, 창업교육, 멘토링을 지원하는 데모 공고입니다."),
                        Map.entry("target", "만 19세 이상 39세 이하 청년 예비창업자"),
                        Map.entry("region", "전국"),
                        Map.entry("startupStage", "예비창업"),
                        Map.entry("hashtags", "창업,청년,사업화,멘토링"),
                        Map.entry("organization", "창업진흥원"),
                        Map.entry("startDate", LocalDate.now().minusDays(5).toString()),
                        Map.entry("endDate", LocalDate.now().plusDays(20).toString()),
                        Map.entry("supportAmount", "최대 5천만원"),
                        Map.entry("documents", "사업계획서, 개인정보동의서, 자격 증빙"),
                        Map.entry("url", "https://www.k-startup.go.kr")
                ),
                Map.ofEntries(
                        Map.entry("id", "demo-seoul-startup-space"),
                        Map.entry("title", "서울 청년창업 공간·교육 지원"),
                        Map.entry("summary", "서울에서 창업을 준비하는 청년에게 입주공간, 교육, 멘토링을 제공하는 데모 공고입니다."),
                        Map.entry("target", "서울 거주 또는 서울 창업 희망 청년 예비창업자"),
                        Map.entry("region", "서울"),
                        Map.entry("startupStage", "예비창업"),
                        Map.entry("hashtags", "창업공간,교육,멘토링"),
                        Map.entry("organization", "서울특별시"),
                        Map.entry("startDate", LocalDate.now().minusDays(1).toString()),
                        Map.entry("endDate", LocalDate.now().plusDays(35).toString()),
                        Map.entry("documents", "신청서, 주민등록 또는 활동지역 증빙, 사업 아이템 소개서"),
                        Map.entry("url", "https://www.seoul.go.kr")
                ),
                Map.ofEntries(
                        Map.entry("id", "demo-smallbiz-loan"),
                        Map.entry("title", "소상공인 창업자 정책자금"),
                        Map.entry("summary", "사업자등록을 완료한 초기 소상공인의 운영자금 대출을 지원하는 데모 공고입니다."),
                        Map.entry("target", "사업자등록증을 보유한 창업 3년 이내 소상공인"),
                        Map.entry("region", "전국"),
                        Map.entry("startupStage", "초기창업"),
                        Map.entry("hashtags", "정책자금,대출"),
                        Map.entry("organization", "소상공인시장진흥공단"),
                        Map.entry("startDate", LocalDate.now().minusDays(30).toString()),
                        Map.entry("endDate", LocalDate.now().plusDays(10).toString()),
                        Map.entry("documents", "사업자등록증, 매출 증빙, 신청서"),
                        Map.entry("url", "https://www.sbiz.or.kr")
                ),
                Map.ofEntries(
                        Map.entry("id", "demo-closed-marketing"),
                        Map.entry("title", "마감된 청년 마케팅 지원사업"),
                        Map.entry("summary", "정렬 테스트를 위한 마감 데모 공고입니다."),
                        Map.entry("target", "청년 창업자"),
                        Map.entry("region", "부산"),
                        Map.entry("startupStage", "초기창업"),
                        Map.entry("hashtags", "마케팅,판로"),
                        Map.entry("organization", "부산광역시"),
                        Map.entry("startDate", LocalDate.now().minusDays(60).toString()),
                        Map.entry("endDate", LocalDate.now().minusDays(2).toString()),
                        Map.entry("documents", "사업계획서"),
                        Map.entry("url", "https://www.busan.go.kr")
                )
        );
        return upsertRaw("demo", demoPrograms);
    }

    private int upsertRaw(String source, List<Map<String, Object>> rawItems) {
        int count = 0;
        for (Map<String, Object> raw : rawItems) {
            SupportProgram incoming = normalizer.normalize(source, raw);
            SupportProgram saved = supportProgramRepository.findBySourceAndSourceId(incoming.getSource(), incoming.getSourceId())
                    .map(existing -> {
                        normalizer.copyInto(incoming, existing);
                        return supportProgramRepository.save(existing);
                    })
                    .orElseGet(() -> supportProgramRepository.save(incoming));
            if (saved.getId() != null) {
                count++;
            }
        }
        return count;
    }

    private Map<String, Object> toAiIndexDocument(SupportProgram program) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("programId", program.getId());
        item.put("source", program.getSource());
        item.put("sourceId", program.getSourceId());
        item.put("title", program.getTitle());
        item.put("summary", program.getSummary());
        item.put("content", program.getContent());
        item.put("category", program.getCategory());
        item.put("supportType", program.getSupportType());
        item.put("target", program.getTarget());
        item.put("ageCondition", program.getAgeCondition());
        item.put("businessStageCondition", program.getBusinessStageCondition());
        item.put("regionCondition", program.getRegionCondition());
        item.put("industryCondition", program.getIndustryCondition());
        item.put("organization", program.getOrganization());
        item.put("department", program.getDepartment());
        item.put("contact", program.getContact());
        item.put("applicationStartDate", program.getApplicationStartDate());
        item.put("applicationEndDate", program.getApplicationEndDate());
        item.put("status", program.getStatus());
        item.put("supportAmount", program.getSupportAmount());
        item.put("requiredDocuments", program.getRequiredDocuments());
        item.put("applyUrl", program.getApplyUrl());
        item.put("detailUrl", program.getDetailUrl());
        item.put("sourceUrl", program.getSourceUrl());
        item.put("tags", program.getTags());
        return item;
    }
}
