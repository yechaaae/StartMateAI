package com.kakao.backend.startupProfile.model;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.user.model.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "startup_profile")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
// 사용자의 창업 준비 상태와 선호 조건을 저장하는 프로필입니다.
public class StartupProfile extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    // 전공 또는 주 학습/전문 분야입니다.
    @Column(name = "major")
    private String major;

    // 창업, 직무, 아르바이트, 프로젝트 등 관련 경험입니다.
    @Column(name = "career")
    private String career;

    // 관심 있는 창업 분야나 업종입니다.
    @Column(name = "interest_field")
    private String interestField;

    // 현재 거주 중인 지역입니다.
    @Column(name = "residence_region")
    private String residenceRegion;

    // 창업을 희망하는 지역입니다.
    @Column(name = "business_region")
    private String businessRegion;

    // 창업에 사용할 수 있는 초기 예산입니다.
    @Column(name = "initial_budget")
    private Integer initialBudget;

    // 개인 창업, 팀 보유, 팀원 모집 중 등 팀 구성 상태입니다.
    @Enumerated(EnumType.STRING)
    @Column(name = "team_status")
    private TeamStatus teamStatus;

    // 온라인, 오프라인, 플랫폼, 소상공인 매장 등 희망 창업 형태입니다.
    @Enumerated(EnumType.STRING)
    @Column(name = "preferred_business_type")
    private PreferredBusinessType preferredBusinessType;

    // 사용자의 강점 키워드나 태그 목록입니다.
    @Lob
    @Column(name = "strength_tags", columnDefinition = "text")
    private String strengthTags;

    // 진단 결과로 계산된 창업 적합도 점수입니다.
    @Column(name = "suitability_score")
    private Integer suitabilityScore;

    // 진단 결과 요약 문장입니다.
    @Lob
    @Column(name = "diagnosis_summary", columnDefinition = "text")
    private String diagnosisSummary;

    // 기본 창업 프로필을 생성합니다.
    public static StartupProfile create() {
        return new StartupProfile();
    }

    // 특정 사용자에게 연결되는 창업 프로필을 생성합니다.
    public static StartupProfile create(User user) {
        StartupProfile startupProfile = create();
        startupProfile.setUser(user);
        return startupProfile;
    }

    // 온보딩에서 입력받은 창업 프로필 값을 반영합니다.
    public void update(
            String major,
            String career,
            String interestField,
            String residenceRegion,
            String businessRegion,
            Integer initialBudget,
            TeamStatus teamStatus,
            PreferredBusinessType preferredBusinessType,
            String strengthTags
    ) {
        this.major = major;
        this.career = career;
        this.interestField = interestField;
        this.residenceRegion = residenceRegion;
        this.businessRegion = businessRegion;
        this.initialBudget = initialBudget;
        this.teamStatus = teamStatus;
        this.preferredBusinessType = preferredBusinessType;
        this.strengthTags = strengthTags;
    }
}
