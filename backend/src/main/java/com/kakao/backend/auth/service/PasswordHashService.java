package com.kakao.backend.auth.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import org.springframework.stereotype.Component;

@Component
// 로컬 로그인 비밀번호를 salt와 함께 해시하고 검증합니다.
public class PasswordHashService {

    private static final String ALGORITHM = "SHA-256";
    private static final int SALT_LENGTH = 16;
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    // 원본 비밀번호를 저장 가능한 해시 문자열로 변환합니다.
    public String encode(String rawPassword) {
        byte[] salt = new byte[SALT_LENGTH];
        SECURE_RANDOM.nextBytes(salt);

        byte[] hash = hash(rawPassword, salt);
        return String.join("$",
                ALGORITHM,
                Base64.getEncoder().encodeToString(salt),
                Base64.getEncoder().encodeToString(hash));
    }

    // 입력 비밀번호를 같은 salt로 다시 해시해 저장된 값과 비교합니다.
    public boolean matches(String rawPassword, String encodedPassword) {
        if (rawPassword == null || encodedPassword == null) {
            return false;
        }

        String[] parts = encodedPassword.split("\\$");
        if (parts.length != 3 || !ALGORITHM.equals(parts[0])) {
            return false;
        }

        byte[] salt = Base64.getDecoder().decode(parts[1]);
        byte[] expectedHash = Base64.getDecoder().decode(parts[2]);
        return MessageDigest.isEqual(expectedHash, hash(rawPassword, salt));
    }

    private byte[] hash(String rawPassword, byte[] salt) {
        try {
            MessageDigest messageDigest = MessageDigest.getInstance(ALGORITHM);
            messageDigest.update(salt);
            return messageDigest.digest(rawPassword.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("Password hash algorithm is unavailable.", exception);
        }
    }
}
