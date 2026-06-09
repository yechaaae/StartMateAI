package com.kakao.backend.user.dto;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.user.model.User;
import org.junit.jupiter.api.Test;

class AuthUserResponseTest {

    @Test
    void 응답은_HTML_특수문자를_escape해서_반환한다() {
        User user = User.createLocal(
                "test@example.com",
                "encodedPassword",
                "<script>alert(1)</script>");
        user.setId(1L);
        user.setRole("<ADMIN>");

        AuthUserResponse response = AuthUserResponse.from(user);

        assertThat(response.nickname()).isEqualTo("&lt;script&gt;alert(1)&lt;/script&gt;");
        assertThat(response.role()).isEqualTo("&lt;ADMIN&gt;");
    }
}
