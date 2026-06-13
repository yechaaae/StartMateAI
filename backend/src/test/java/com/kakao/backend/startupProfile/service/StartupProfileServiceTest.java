package com.kakao.backend.startupProfile.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

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
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

@ExtendWith(MockitoExtension.class)
class StartupProfileServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private StartupProfileRepository startupProfileRepository;

    private StartupProfileService startupProfileService;

    @BeforeEach
    void setUp() {
        startupProfileService = new StartupProfileService(userRepository, startupProfileRepository);
    }

    @Test
    void 프로필이_없으면_온보딩이_필요하고_전체_필드를_누락으로_반환한다() {
        given(userRepository.findById(1L)).willReturn(Optional.of(user()));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());

        StartupProfileStatusResponse response = startupProfileService.getStatus(1L);

        assertThat(response.profileExists()).isFalse();
        assertThat(response.profileCompleted()).isFalse();
        assertThat(response.requiresOnboarding()).isTrue();
        assertThat(response.missingFields()).containsExactly(
                "stage",
                "major",
                "career",
                "interestField",
                "residenceRegion",
                "businessRegion",
                "teamStatus",
                "preferredBusinessType",
                "strengthTags");
    }

    @Test
    void 프로필에_빈_값이_있으면_해당_필드만_누락으로_반환한다() {
        User user = user();
        StartupProfile profile = StartupProfile.create(user);
        profile.update(
                StartupStage.PRE_STARTUP,
                "컴퓨터공학",
                "",
                "푸드테크",
                "서울",
                "서울 강남구",
                10_000_000,
                TeamStatus.SOLO,
                PreferredBusinessType.ONLINE,
                "기획, 실행력",
                null,
                null,
                null);
        user.updateStartupProfile(profile);
        given(userRepository.findById(1L)).willReturn(Optional.of(user));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.of(profile));

        StartupProfileStatusResponse response = startupProfileService.getStatus(1L);

        assertThat(response.profileExists()).isTrue();
        assertThat(response.profileCompleted()).isFalse();
        assertThat(response.requiresOnboarding()).isTrue();
        assertThat(response.missingFields()).containsExactly("career");
    }

    @Test
    void 프로필을_입력하면_검증한_값으로_새_프로필을_생성한다() {
        User user = user();
        given(userRepository.findById(1L)).willReturn(Optional.of(user));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());
        given(startupProfileRepository.save(any(StartupProfile.class))).willAnswer(invocation -> {
            StartupProfile profile = invocation.getArgument(0);
            profile.setId(1L);
            return profile;
        });

        StartupProfileResponse response = startupProfileService.saveProfile(1L, validRequest());

        ArgumentCaptor<StartupProfile> profileCaptor = ArgumentCaptor.forClass(StartupProfile.class);
        verify(startupProfileRepository).save(profileCaptor.capture());
        StartupProfile savedProfile = profileCaptor.getValue();

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.major()).isEqualTo("컴퓨터공학");
        assertThat(response.initialBudget()).isEqualTo(10_000_000);
        assertThat(savedProfile.getUser()).isSameAs(user);
        assertThat(user.getStartupProfile()).isSameAs(savedProfile);
    }

    @Test
    void 프로필을_다시_입력하면_기존_프로필을_수정한다() {
        User user = user();
        StartupProfile profile = StartupProfile.create(user);
        profile.setId(1L);
        user.updateStartupProfile(profile);
        given(userRepository.findById(1L)).willReturn(Optional.of(user));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.of(profile));
        given(startupProfileRepository.save(profile)).willReturn(profile);

        StartupProfileRequest request = new StartupProfileRequest(
                StartupStage.PRE_STARTUP,
                "디자인",
                "브랜딩 경험",
                "로컬",
                "부산",
                "부산 해운대구",
                5_000_000,
                TeamStatus.HAS_TEAM,
                PreferredBusinessType.OFFLINE,
                "콘텐츠, 브랜딩",
                null,
                null,
                null);

        StartupProfileResponse response = startupProfileService.saveProfile(1L, request);

        assertThat(response.major()).isEqualTo("디자인");
        assertThat(response.businessRegion()).isEqualTo("부산 해운대구");
        assertThat(profile.getCareer()).isEqualTo("브랜딩 경험");
    }

    @Test
    void 프로필_요청_body가_비어있으면_실패한다() {
        assertThatThrownBy(() -> startupProfileService.saveProfile(1L, null))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(userRepository, never()).findById(1L);
        verify(startupProfileRepository, never()).save(any(StartupProfile.class));
    }

    @Test
    void 프로필_입력값에_HTML_태그가_있으면_실패한다() {
        given(userRepository.findById(1L)).willReturn(Optional.of(user()));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());
        StartupProfileRequest request = new StartupProfileRequest(
                StartupStage.PRE_STARTUP,
                "컴퓨터공학",
                "<script>alert(1)</script>",
                "푸드테크",
                "서울",
                "서울 강남구",
                10_000_000,
                TeamStatus.SOLO,
                PreferredBusinessType.ONLINE,
                "기획, 실행력",
                null,
                null,
                null);

        assertThatThrownBy(() -> startupProfileService.saveProfile(1L, request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(startupProfileRepository, never()).save(any(StartupProfile.class));
    }

    @Test
    void 프로필_초기_예산이_음수이면_실패한다() {
        given(userRepository.findById(1L)).willReturn(Optional.of(user()));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());
        StartupProfileRequest request = new StartupProfileRequest(
                StartupStage.PRE_STARTUP,
                "컴퓨터공학",
                "개발 경험",
                "푸드테크",
                "서울",
                "서울 강남구",
                -1,
                TeamStatus.SOLO,
                PreferredBusinessType.ONLINE,
                "기획, 실행력",
                null,
                null,
                null);

        assertThatThrownBy(() -> startupProfileService.saveProfile(1L, request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(startupProfileRepository, never()).save(any(StartupProfile.class));
    }

    @Test
    void 창업_후_프로필은_현재_아이템_정보로_저장한다() {
        User user = user();
        given(userRepository.findById(1L)).willReturn(Optional.of(user));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());
        given(startupProfileRepository.save(any(StartupProfile.class))).willAnswer(invocation -> {
            StartupProfile profile = invocation.getArgument(0);
            profile.setId(1L);
            return profile;
        });

        StartupProfileRequest request = new StartupProfileRequest(
                StartupStage.POST_STARTUP,
                "시각디자인",
                "카페 매니저 1년",
                "F&B",
                "부산",
                "부산 해운대구 구남로",
                null,
                TeamStatus.SOLO,
                PreferredBusinessType.LOCAL_STORE,
                "브랜딩, SNS",
                "구남로 수제 쿠키",
                "카페",
                OperatingPeriod.SIX_TO_12M);

        StartupProfileResponse response = startupProfileService.saveProfile(1L, request);

        ArgumentCaptor<StartupProfile> profileCaptor = ArgumentCaptor.forClass(StartupProfile.class);
        verify(startupProfileRepository).save(profileCaptor.capture());
        StartupProfile savedProfile = profileCaptor.getValue();

        assertThat(response.stage()).isEqualTo("POST_STARTUP");
        assertThat(response.currentItemName()).isEqualTo("구남로 수제 쿠키");
        assertThat(response.currentIndustry()).isEqualTo("카페");
        assertThat(response.operatingPeriod()).isEqualTo("SIX_TO_12M");
        assertThat(response.initialBudget()).isNull();
        assertThat(savedProfile.getInitialBudget()).isNull();
        assertThat(savedProfile.getStage()).isEqualTo(StartupStage.POST_STARTUP);
    }

    @Test
    void 창업_후_프로필에_아이템_정보가_없으면_실패한다() {
        given(userRepository.findById(1L)).willReturn(Optional.of(user()));
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());
        StartupProfileRequest request = new StartupProfileRequest(
                StartupStage.POST_STARTUP,
                "시각디자인",
                "카페 매니저 1년",
                "F&B",
                "부산",
                "부산 해운대구 구남로",
                null,
                TeamStatus.SOLO,
                PreferredBusinessType.LOCAL_STORE,
                "브랜딩, SNS",
                "",
                "카페",
                OperatingPeriod.SIX_TO_12M);

        assertThatThrownBy(() -> startupProfileService.saveProfile(1L, request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(startupProfileRepository, never()).save(any(StartupProfile.class));
    }

    @Test
    void 창업_단계가_없으면_실패한다() {
        StartupProfileRequest request = new StartupProfileRequest(
                null,
                "컴퓨터공학",
                "개발 경험",
                "푸드테크",
                "서울",
                "서울 강남구",
                10_000_000,
                TeamStatus.SOLO,
                PreferredBusinessType.ONLINE,
                "기획, 실행력",
                null,
                null,
                null);

        assertThatThrownBy(() -> startupProfileService.saveProfile(1L, request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(startupProfileRepository, never()).save(any(StartupProfile.class));
    }

    @Test
    void 프로필_상세_조회는_프로필이_없으면_실패한다() {
        given(startupProfileRepository.findByUserId(1L)).willReturn(Optional.empty());

        assertThatThrownBy(() -> startupProfileService.getProfile(1L))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.NOT_FOUND);
    }

    private User user() {
        User user = User.createLocal("test@example.com", "encodedPassword", "카카오유저");
        user.setId(1L);
        return user;
    }

    private StartupProfileRequest validRequest() {
        return new StartupProfileRequest(
                StartupStage.PRE_STARTUP,
                "컴퓨터공학",
                "개발 경험",
                "푸드테크",
                "서울",
                "서울 강남구",
                10_000_000,
                TeamStatus.SOLO,
                PreferredBusinessType.ONLINE,
                "기획, 실행력",
                null,
                null,
                null);
    }
}
