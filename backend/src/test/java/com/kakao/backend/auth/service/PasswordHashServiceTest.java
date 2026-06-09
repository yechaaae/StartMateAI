package com.kakao.backend.auth.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PasswordHashServiceTest {

    private final PasswordHashService passwordHashService = new PasswordHashService();

    @Test
    void 비밀번호는_원문이_아닌_해시로_저장되고_다시_검증할_수_있다() {
        String encodedPassword = passwordHashService.encode("password123");

        assertThat(encodedPassword).isNotEqualTo("password123");
        assertThat(passwordHashService.matches("password123", encodedPassword)).isTrue();
    }

    @Test
    void 잘못된_비밀번호는_검증에_실패한다() {
        String encodedPassword = passwordHashService.encode("password123");

        assertThat(passwordHashService.matches("wrongpassword", encodedPassword)).isFalse();
    }
}
