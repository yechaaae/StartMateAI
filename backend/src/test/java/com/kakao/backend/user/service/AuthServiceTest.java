package com.kakao.backend.user.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.kakao.backend.user.dto.AuthUserResponse;
import com.kakao.backend.user.dto.LoginRequest;
import com.kakao.backend.user.dto.SignupRequest;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.http.HttpStatus;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    private PasswordHashService passwordHashService;
    private AuthService authService;

    @BeforeEach
    void setUp() {
        passwordHashService = new PasswordHashService();
        authService = new AuthService(userRepository, passwordHashService);
    }

    @Test
    void 회원가입에_성공하면_비밀번호를_해시하고_사용자_정보를_반환한다() {
        SignupRequest request = new SignupRequest(
                " Test@Example.com ",
                "password123",
                "password123",
                "카카오유저");

        given(userRepository.existsByEmail("test@example.com")).willReturn(false);
        given(userRepository.save(any(User.class))).willAnswer(invocation -> {
            User user = invocation.getArgument(0);
            user.setId(1L);
            return user;
        });

        AuthUserResponse response = authService.signup(request);

        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(userCaptor.capture());
        User savedUser = userCaptor.getValue();

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.email()).isEqualTo("test@example.com");
        assertThat(response.nickname()).isEqualTo("카카오유저");
        assertThat(response.role()).isEqualTo("USER");
        assertThat(savedUser.getPassword()).isNotEqualTo("password123");
        assertThat(passwordHashService.matches("password123", savedUser.getPassword())).isTrue();
    }

    @Test
    void 회원가입은_이미_가입된_이메일이면_실패한다() {
        SignupRequest request = new SignupRequest(
                "test@example.com",
                "password123",
                "password123",
                "카카오유저");

        given(userRepository.existsByEmail("test@example.com")).willReturn(true);

        assertThatThrownBy(() -> authService.signup(request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.CONFLICT);

        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void 회원가입은_비밀번호_확인이_다르면_실패한다() {
        SignupRequest request = new SignupRequest(
                "test@example.com",
                "password123",
                "password456",
                "카카오유저");

        assertThatThrownBy(() -> authService.signup(request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void 회원가입은_스크립트가_포함된_닉네임이면_실패한다() {
        SignupRequest request = new SignupRequest(
                "test@example.com",
                "password123",
                "password123",
                "<script>alert(1)</script>");

        assertThatThrownBy(() -> authService.signup(request))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.BAD_REQUEST);

        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void 로그인은_올바른_이메일과_비밀번호면_사용자_정보를_반환한다() {
        User user = User.createLocal("test@example.com", passwordHashService.encode("password123"), "카카오유저");
        user.setId(1L);

        given(userRepository.findByEmail("test@example.com")).willReturn(Optional.of(user));

        AuthUserResponse response = authService.login(new LoginRequest("test@example.com", "password123"));

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.email()).isEqualTo("test@example.com");
        assertThat(response.nickname()).isEqualTo("카카오유저");
    }

    @Test
    void 로그인은_비밀번호가_틀리면_실패한다() {
        User user = User.createLocal("test@example.com", passwordHashService.encode("password123"), "카카오유저");
        user.setId(1L);

        given(userRepository.findByEmail("test@example.com")).willReturn(Optional.of(user));

        assertThatThrownBy(() -> authService.login(new LoginRequest("test@example.com", "wrongpassword")))
                .isInstanceOf(AuthException.class)
                .extracting("status")
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void 현재_사용자는_세션의_사용자_id로_조회한다() {
        User user = User.createLocal("test@example.com", passwordHashService.encode("password123"), "카카오유저");
        user.setId(1L);

        given(userRepository.findById(1L)).willReturn(Optional.of(user));

        AuthUserResponse response = authService.getCurrentUser(1L);

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.email()).isEqualTo("test@example.com");
    }
}
