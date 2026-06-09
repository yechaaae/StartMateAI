package com.kakao.backend.startupProfile.model;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class StartupProfileEnumTest {

    @Test
    void 팀_구성_상태는_코드와_한글_라벨로_변환할_수_있다() {
        assertThat(TeamStatus.from("SOLO")).isEqualTo(TeamStatus.SOLO);
        assertThat(TeamStatus.from("개인")).isEqualTo(TeamStatus.SOLO);
        assertThat(TeamStatus.from("팀 있음")).isEqualTo(TeamStatus.HAS_TEAM);
    }

    @Test
    void 희망_창업_형태는_코드와_한글_라벨로_변환할_수_있다() {
        assertThat(PreferredBusinessType.from("ONLINE")).isEqualTo(PreferredBusinessType.ONLINE);
        assertThat(PreferredBusinessType.from("온라인")).isEqualTo(PreferredBusinessType.ONLINE);
        assertThat(PreferredBusinessType.from("오프라인")).isEqualTo(PreferredBusinessType.OFFLINE);
    }

    @Test
    void 정의되지_않은_enum_값은_변환에_실패한다() {
        assertThatThrownBy(() -> TeamStatus.from("아무 값"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PreferredBusinessType.from("아무 값"))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
