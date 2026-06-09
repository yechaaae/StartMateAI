package com.kakao.backend.user.application;

import java.time.LocalDateTime;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class TestUserSeedService implements ApplicationRunner {

    private final JdbcTemplate jdbcTemplate;
    private final boolean enabled;
    private final Long userId;
    private final String email;
    private final String nickname;
    private final String role;

    public TestUserSeedService(
            JdbcTemplate jdbcTemplate,
            @Value("${app.seed.test-user.enabled:true}") boolean enabled,
            @Value("${app.seed.test-user.id:1}") Long userId,
            @Value("${app.seed.test-user.email:test-user@startmate.local}") String email,
            @Value("${app.seed.test-user.nickname:tester}") String nickname,
            @Value("${app.seed.test-user.role:USER}") String role
    ) {
        this.jdbcTemplate = jdbcTemplate;
        this.enabled = enabled;
        this.userId = userId;
        this.email = email;
        this.nickname = nickname;
        this.role = role;
    }

    @Override
    public void run(ApplicationArguments args) {
        seed();
    }

    void seed() {
        if (!enabled) {
            return;
        }

        if (existsById(userId) || existsByEmail(email)) {
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        jdbcTemplate.update(
                "insert into users (id, email, password, nickname, provider, role, created_at, updated_at) "
                        + "values (?, ?, ?, ?, ?, ?, ?, ?)",
                userId,
                email,
                null,
                nickname,
                null,
                role,
                now,
                now
        );
    }

    private boolean existsById(Long id) {
        Integer count = jdbcTemplate.queryForObject(
                "select count(*) from users where id = ?",
                Integer.class,
                id
        );
        return count != null && count > 0;
    }

    private boolean existsByEmail(String targetEmail) {
        Integer count = jdbcTemplate.queryForObject(
                "select count(*) from users where email = ?",
                Integer.class,
                targetEmail
        );
        return count != null && count > 0;
    }
}
