package com.kakao.backend.user.application;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.jdbc.core.JdbcTemplate;

@ExtendWith(MockitoExtension.class)
class TestUserSeedServiceTest {

    @Mock
    private JdbcTemplate jdbcTemplate;

    @Test
    void insertsDefaultTestUserWhenMissing() {
        TestUserSeedService service = new TestUserSeedService(
                jdbcTemplate,
                true,
                1L,
                "test-user@startmate.local",
                "tester",
                "USER"
        );

        when(jdbcTemplate.queryForObject(
                "select count(*) from users where id = ?",
                Integer.class,
                1L
        )).thenReturn(0);
        when(jdbcTemplate.queryForObject(
                "select count(*) from users where email = ?",
                Integer.class,
                "test-user@startmate.local"
        )).thenReturn(0);

        service.seed();

        verify(jdbcTemplate).update(
                eq("insert into users (id, email, password, nickname, provider, role, created_at, updated_at) "
                        + "values (?, ?, ?, ?, ?, ?, ?, ?)"),
                eq(1L),
                eq("test-user@startmate.local"),
                eq(null),
                eq("tester"),
                eq(null),
                eq("USER"),
                any(LocalDateTime.class),
                any(LocalDateTime.class)
        );
    }

    @Test
    void skipsInsertWhenTestUserAlreadyExists() {
        TestUserSeedService service = new TestUserSeedService(
                jdbcTemplate,
                true,
                1L,
                "test-user@startmate.local",
                "tester",
                "USER"
        );

        when(jdbcTemplate.queryForObject(
                "select count(*) from users where id = ?",
                Integer.class,
                1L
        )).thenReturn(1);

        service.seed();

        verify(jdbcTemplate, never()).update(any(String.class), any(Object[].class));
    }
}
