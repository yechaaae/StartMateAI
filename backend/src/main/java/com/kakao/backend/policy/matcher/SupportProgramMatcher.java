package com.kakao.backend.policy.matcher;

import com.kakao.backend.policy.domain.SupportProgram;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Component;

@Component
public class SupportProgramMatcher {

    public RecommendedProgramResponse match(SupportProgram program, SupportProgramRecommendationRequest profile) {
        int score = 0;
        List<String> reasons = new ArrayList<>();
        List<String> cautions = new ArrayList<>();

        score += ageScore(program, profile, reasons, cautions);
        score += regionScore(program, profile, reasons, cautions);
        score += stageScore(program, profile, reasons, cautions);
        score += supportTypeScore(program, profile, reasons);
        score += industryScore(program, profile, reasons);
        score += statusScore(program, reasons, cautions);
        score += registrationScore(program, profile, cautions);
        score += businessAgeScore(program, profile, cautions);

        return new RecommendedProgramResponse(
                program.getId(),
                program.getTitle(),
                program.getSource(),
                program.getSummary(),
                Math.max(0, score),
                reasons,
                cautions,
                program.getApplicationEndDate(),
                firstNonBlank(program.getApplyUrl(), program.getDetailUrl())
        );
    }

    private int ageScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> reasons, List<String> cautions) {
        String ageCondition = lower(program.getAgeCondition() + " " + program.getTarget());
        if (ageCondition.isBlank() || ageCondition.equals("null null")) {
            reasons.add("연령 조건이 명확하지 않아 별도 확인이 필요합니다.");
            return 8;
        }
        if (!ageCondition.contains("청년") && !ageCondition.contains("youth") && !ageCondition.matches(".*(19|34|39).*")) {
            reasons.add("연령 제한이 강하게 드러나지 않습니다.");
            return 10;
        }
        if (profile.age() != null && profile.age() >= 19 && profile.age() <= 39) {
            reasons.add("청년 연령 조건에 맞을 가능성이 높습니다.");
            return 30;
        }
        cautions.add("청년 연령 조건과 맞지 않을 수 있습니다.");
        return -30;
    }

    private int regionScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> reasons, List<String> cautions) {
        String condition = text(program.getRegionCondition());
        String desiredSido = text(profile.desiredSido());
        String desiredSigungu = text(profile.desiredSigungu());
        if (condition.isBlank() || containsAny(condition, "전국", "전체")) {
            reasons.add("전국 또는 지역 제한이 약한 공고입니다.");
            return 20;
        }
        if (!desiredSido.isBlank() && condition.contains(desiredSido)) {
            reasons.add("희망 시도와 지역 조건이 맞습니다.");
            return 20;
        }
        if (!desiredSigungu.isBlank() && condition.contains(desiredSigungu)) {
            reasons.add("희망 시군구와 지역 조건이 맞습니다.");
            return 20;
        }
        cautions.add("희망 지역과 공고 지역 조건이 다를 수 있습니다.");
        return -20;
    }

    private int stageScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> reasons, List<String> cautions) {
        String condition = lower(program.getBusinessStageCondition() + " " + program.getTarget() + " " + program.getTitle());
        String stage = lower(profile.businessStage());
        String founderType = lower(profile.founderType());
        if (condition.isBlank() || condition.equals("null null null")) {
            return 5;
        }
        if (containsAny(condition, stage, founderType)
                || (containsAny(condition, "예비", "pre_founder") && containsAny(stage + founderType, "idea", "preparing", "pre_founder"))
                || (containsAny(condition, "초기", "initial") && containsAny(stage, "mvp", "pre_revenue", "revenue"))) {
            reasons.add("창업 단계 조건에 맞을 가능성이 높습니다.");
            return 20;
        }
        cautions.add("창업 단계 조건이 다를 수 있습니다.");
        return -10;
    }

    private int supportTypeScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> reasons) {
        if (profile.interestedSupportTypes() == null || profile.interestedSupportTypes().isEmpty()) {
            return 0;
        }
        if (profile.interestedSupportTypes().contains(program.getSupportType())) {
            reasons.add("관심 지원유형과 일치합니다.");
            return 15;
        }
        return 0;
    }

    private int industryScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> reasons) {
        String condition = text(program.getIndustryCondition());
        if (condition.isBlank()) {
            return 5;
        }
        if (containsAny(condition, profile.industryLarge(), profile.industryMedium(), profile.industrySmall())) {
            reasons.add("업종 조건과 일부 일치합니다.");
            return 10;
        }
        return 0;
    }

    private int statusScore(SupportProgram program, List<String> reasons, List<String> cautions) {
        if ("open".equals(program.getStatus())) {
            reasons.add("현재 모집중으로 판단됩니다.");
            return 5;
        }
        if ("closed".equals(program.getStatus())) {
            cautions.add("마감된 공고일 수 있습니다.");
            return -30;
        }
        if ("upcoming".equals(program.getStatus())) {
            reasons.add("모집 예정 공고입니다.");
            return 2;
        }
        cautions.add("모집 상태를 실제 공고에서 확인해야 합니다.");
        return 0;
    }

    private int registrationScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> cautions) {
        String text = lower(program.getTarget() + " " + program.getRequiredDocuments());
        boolean requiresRegistration = containsAny(text, "사업자등록증", "사업자등록 필수", "사업자 등록 필수");
        if (requiresRegistration && !Boolean.TRUE.equals(profile.businessRegistered())) {
            cautions.add("사업자등록이 필요할 수 있습니다.");
            return -20;
        }
        return 0;
    }

    private int businessAgeScore(SupportProgram program, SupportProgramRecommendationRequest profile, List<String> cautions) {
        if (profile.businessStartDate() == null) {
            return 0;
        }
        long months = ChronoUnit.MONTHS.between(profile.businessStartDate(), LocalDate.now());
        String text = lower(program.getTarget() + " " + program.getBusinessStageCondition());
        if (containsAny(text, "7년", "10년") || months <= 84) {
            return 0;
        }
        if (containsAny(text, "3년", "초기") && months > 36) {
            cautions.add("업력 조건이 맞지 않을 수 있습니다.");
            return -15;
        }
        return 0;
    }

    private boolean containsAny(String text, String... terms) {
        String safeText = text(text);
        for (String term : terms) {
            if (term != null && !term.isBlank() && safeText.contains(term)) {
                return true;
            }
        }
        return false;
    }

    private String text(String value) {
        return value == null || "null".equals(value) ? "" : value;
    }

    private String lower(String value) {
        return text(value).toLowerCase(Locale.ROOT);
    }

    private String firstNonBlank(String first, String second) {
        return first != null && !first.isBlank() ? first : second;
    }
}
