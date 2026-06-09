package com.kakao.backend.user.service;

import com.kakao.backend.user.dto.AuthUserResponse;
import com.kakao.backend.user.dto.LoginRequest;
import com.kakao.backend.user.dto.SignupRequest;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import java.util.regex.Pattern;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
// 인증 요청의 검증, 사용자 조회, 비밀번호 확인 같은 핵심 로직을 처리합니다.
public class AuthService {

    private static final Pattern EMAIL_PATTERN = Pattern.compile(
            "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");
    private static final Pattern NICKNAME_PATTERN = Pattern.compile(
            "^[\\p{IsHangul}A-Za-z0-9_-]{2,20}$");

    private final UserRepository userRepository;
    private final PasswordHashService passwordHashService;

    // 회원가입 입력값을 검증하고 비밀번호를 해시해 사용자로 저장합니다.
    @Transactional
    public AuthUserResponse signup(SignupRequest request) {
        String email = normalizeEmail(request.email());
        String nickname = normalizeNickname(request.nickname());
        String password = requirePassword(request.password());
        String passwordConfirm = requirePassword(request.passwordConfirm());

        if (!password.equals(passwordConfirm)) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "비밀번호와 비밀번호 확인이 일치하지 않습니다.");
        }

        if (userRepository.existsByEmail(email)) {
            throw new AuthException(HttpStatus.CONFLICT, "이미 가입된 이메일입니다.");
        }

        User user = User.createLocal(email, passwordHashService.encode(password), nickname);
        return AuthUserResponse.from(userRepository.save(user));
    }

    // 이메일로 사용자를 찾고 입력된 비밀번호가 저장된 해시와 일치하는지 확인합니다.
    @Transactional(readOnly = true)
    public AuthUserResponse login(LoginRequest request) {
        String email = normalizeEmail(request.email());
        String password = requirePassword(request.password());

        User user = userRepository.findByEmail(email)
                .orElseThrow(this::invalidCredential);

        if (!passwordHashService.matches(password, user.getPassword())) {
            throw invalidCredential();
        }

        return AuthUserResponse.from(user);
    }

    // 세션에 저장된 사용자 id가 실제 사용자와 연결되는지 확인합니다.
    @Transactional(readOnly = true)
    public AuthUserResponse getCurrentUser(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."));
        return AuthUserResponse.from(user);
    }

    private String normalizeEmail(String email) {
        if (email == null || email.isBlank()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "이메일을 입력해주세요.");
        }

        String normalizedEmail = email.trim().toLowerCase();
        if (!EMAIL_PATTERN.matcher(normalizedEmail).matches()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "올바른 이메일 형식이 아닙니다.");
        }
        return normalizedEmail;
    }

    private String normalizeNickname(String nickname) {
        if (nickname == null || nickname.isBlank()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "닉네임을 입력해주세요.");
        }

        String normalizedNickname = nickname.trim();
        if (!NICKNAME_PATTERN.matcher(normalizedNickname).matches()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "닉네임은 한글, 영문, 숫자, _, - 조합으로 2~20자만 사용할 수 있습니다.");
        }
        return normalizedNickname;
    }

    private String requirePassword(String password) {
        if (password == null || password.isBlank()) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "비밀번호를 입력해주세요.");
        }
        if (password.length() < 8) {
            throw new AuthException(HttpStatus.BAD_REQUEST, "비밀번호는 8자 이상이어야 합니다.");
        }
        return password;
    }

    private AuthException invalidCredential() {
        return new AuthException(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.");
    }
}
