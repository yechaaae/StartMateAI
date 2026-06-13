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
        return new SupportProgramSyncResponse(counts, (int) supportProgramRepository.countBySourceNot("demo"));
    }

    @Transactional(readOnly = true)
    public List<RecommendedProgramResponse> recommend(SupportProgramRecommendationRequest request) {
        List<SupportProgram> programs = realPrograms();
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
        return realPrograms().stream()
                .map(this::toAiIndexDocument)
                .toList();
    }

    private List<SupportProgram> realPrograms() {
        return supportProgramRepository.findAll().stream()
                .filter(program -> !"demo".equals(program.getSource()))
                .toList();
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
