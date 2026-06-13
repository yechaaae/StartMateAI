package com.kakao.backend.startupProfile.service;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.startupProfile.dto.StartupProfileRequest;
import com.kakao.backend.startupProfile.dto.StartupProfileResponse;
import com.kakao.backend.startupProfile.dto.StartupProfileStatusResponse;
import com.kakao.backend.startupProfile.model.OperatingPeriod;
import com.kakao.backend.startupProfile.model.PreferredBusinessType;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.startupProfile.model.StartupStage;
import com.kakao.backend.startupProfile.model.TeamStatus;
import com.kakao.backend.startupProfile.repository.StartupProfileRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
// 창업 프로필의 온보딩 필요 여부 확인과 생성/수정을 담당합니다.
public class StartupProfileService {

    private static final int SHORT_TEXT_MAX_LENGTH = 50;
    private static final int TAG_TEXT_MAX_LENGTH = 200;
    private static final int LONG_TEXT_MAX_LENGTH = 500;
    private static final int MAX_INITIAL_BUDGET = 1_000_000_000;

    private final UserRepository userRepository;
    private final StartupProfileRepository startupProfileRepository;

    // 현재 사용자의 프로필 존재 여부와 비어 있는 필드를 확인합니다.
    @Transactional(readOnly = true)
    public StartupProfileStatusResponse getStatus(Long userId) {
        getUser(userId);
        StartupProfile profile = startupProfileRepository.findByUserId(userId).orElse(null);
        boolean exists = profile != null;
        return StartupProfileStatusResponse.of(exists, missingFields(profile));
    }

    // 현재 사용자의 창업 프로필을 조회합니다.
    @Transactional(readOnly = true)
    public StartupProfileResponse getProfile(Long userId) {
        StartupProfile profile = startupProfileRepository.findByUserId(userId)
                .orElseThrow(() -> new AuthException(HttpStatus.NOT_FOUND, "창업 프로필이 없습니다."));
        return StartupProfileResponse.from(profile);
    }

    // 온보딩 입력값을 검증한 뒤 프로필을 새로 만들거나 기존 프로필을 갱신합니다.
    @Transactional
    public StartupProfileResponse saveProfile(Long userId, StartupProfileRequest request) {
        if (request == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "창업 프로필 정보를 입력해주세요.");
        }

        StartupStage stage = requireStage(request.stage());
        boolean postStartup = stage == StartupStage.POST_STARTUP;

        User user = getUser(userId);
        StartupProfile profile = startupProfileRepository.findByUserId(userId)
                .orElseGet(() -> {
                    StartupProfile newProfile = StartupProfile.create(user);
                    user.updateStartupProfile(newProfile);
                    return newProfile;
                });

        // 공통 항목 검증
        String major = requireText("전공", request.major(), TAG_TEXT_MAX_LENGTH);
        String career = requireText("경력", request.career(), LONG_TEXT_MAX_LENGTH);
        String interestField = requireText("관심 분야", request.interestField(), TAG_TEXT_MAX_LENGTH);
        String residenceRegion = requireText("거주 지역", request.residenceRegion(), SHORT_TEXT_MAX_LENGTH);
        String businessRegion = requireText(
                postStartup ? "사업장 위치" : "사업 희망 지역", request.businessRegion(), SHORT_TEXT_MAX_LENGTH);
        TeamStatus teamStatus = requireTeamStatus(request.teamStatus());
        PreferredBusinessType preferredBusinessType = requirePreferredBusinessType(request.preferredBusinessType());
        String strengthTags = requireText("강점 태그", request.strengthTags(), LONG_TEXT_MAX_LENGTH);

        // 단계별 전용 항목 검증
        Integer initialBudget = null;
        String currentItemName = null;
        String currentIndustry = null;
        OperatingPeriod operatingPeriod = null;
        if (postStartup) {
            currentItemName = requireText("현재 아이템", request.currentItemName(), SHORT_TEXT_MAX_LENGTH);
            currentIndustry = requireText("업종", request.currentIndustry(), SHORT_TEXT_MAX_LENGTH);
            operatingPeriod = requireOperatingPeriod(request.operatingPeriod());
        } else {
            initialBudget = requireInitialBudget(request.initialBudget());
        }

        profile.update(
                stage,
                major,
                career,
                interestField,
                residenceRegion,
                businessRegion,
                initialBudget,
                teamStatus,
                preferredBusinessType,
                strengthTags,
                currentItemName,
                currentIndustry,
                operatingPeriod);

        return StartupProfileResponse.from(startupProfileRepository.save(profile));
    }

    private User getUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."));
    }

    private List<String> missingFields(StartupProfile profile) {
        List<String> fields = new ArrayList<>();
        // 프로필 자체가 없으면 단계 선택부터 시작해야 합니다.
        if (profile == null) {
            fields.addAll(List.of(
                    "stage",
                    "major",
                    "career",
                    "interestField",
                    "residenceRegion",
                    "businessRegion",
                    "teamStatus",
                    "preferredBusinessType",
                    "strengthTags"));
            return fields;
        }

        addIfBlank(fields, "major", profile.getMajor());
        addIfBlank(fields, "career", profile.getCareer());
        addIfBlank(fields, "interestField", profile.getInterestField());
        addIfBlank(fields, "residenceRegion", profile.getResidenceRegion());
        addIfBlank(fields, "businessRegion", profile.getBusinessRegion());
        if (profile.getTeamStatus() == null) {
            fields.add("teamStatus");
        }
        if (profile.getPreferredBusinessType() == null) {
            fields.add("preferredBusinessType");
        }
        addIfBlank(fields, "strengthTags", profile.getStrengthTags());

        // 단계별 전용 항목 (stage가 null인 과거 프로필은 창업 전으로 간주합니다.)
        if (profile.getStage() == StartupStage.POST_STARTUP) {
            addIfBlank(fields, "currentItemName", profile.getCurrentItemName());
            addIfBlank(fields, "currentIndustry", profile.getCurrentIndustry());
            if (profile.getOperatingPeriod() == null) {
                fields.add("operatingPeriod");
            }
        } else if (profile.getInitialBudget() == null || profile.getInitialBudget() < 0) {
            fields.add("initialBudget");
        }
        return fields;
    }

    private void addIfBlank(List<String> fields, String fieldName, String value) {
        if (value == null || value.isBlank()) {
            fields.add(fieldName);
        }
    }

    private String requireText(String fieldName, String value, int maxLength) {
        if (value == null || value.isBlank()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, fieldName + "을(를) 입력해주세요.");
        }

        String normalizedValue = value.trim();
        if (normalizedValue.length() > maxLength) {
            throw new AuthException(HttpStatus.BAD_REQUEST, fieldName + "은(는) " + maxLength + "자 이하로 입력해주세요.");
        }
        if (containsHtmlDelimiter(normalizedValue)) {
            throw new AuthException(HttpStatus.BAD_REQUEST, fieldName + "에는 HTML 태그를 사용할 수 없습니다.");
        }
        return normalizedValue;
    }

    private Integer requireInitialBudget(Integer initialBudget) {
        if (initialBudget == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "초기 예산을 입력해주세요.");
        }
        if (initialBudget < 0 || initialBudget > MAX_INITIAL_BUDGET) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "초기 예산은 0원 이상 10억원 이하로 입력해주세요.");
        }
        return initialBudget;
    }

    private TeamStatus requireTeamStatus(TeamStatus teamStatus) {
        if (teamStatus == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "팀 구성 상태를 선택해주세요.");
        }
        return teamStatus;
    }

    private PreferredBusinessType requirePreferredBusinessType(PreferredBusinessType preferredBusinessType) {
        if (preferredBusinessType == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "희망 창업 형태를 선택해주세요.");
        }
        return preferredBusinessType;
    }

    private StartupStage requireStage(StartupStage stage) {
        if (stage == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "창업 단계를 선택해주세요.");
        }
        return stage;
    }

    private OperatingPeriod requireOperatingPeriod(OperatingPeriod operatingPeriod) {
        if (operatingPeriod == null) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "운영 기간을 선택해주세요.");
        }
        return operatingPeriod;
    }

    private boolean containsHtmlDelimiter(String value) {
        return value.contains("<") || value.contains(">");
    }
}
