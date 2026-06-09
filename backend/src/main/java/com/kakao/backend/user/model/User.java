package com.kakao.backend.user.model;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.workspace.domain.Workspace;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.List;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "users")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
// 서비스에 가입한 사용자의 계정 정보와 연결된 작업 공간을 표현합니다.
public class User extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "email", nullable = false, unique = true)
    private String email;

    @Column(name = "password")
    private String password;

    @Column(name = "nickname", nullable = false)
    private String nickname;

    @Column(name = "provider")
    private String provider;

    @Column(name = "role", nullable = false)
    private String role;

    @OneToOne(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private StartupProfile startupProfile;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Workspace> workspaces = new ArrayList<>();

    // 외부 로그인 등 비밀번호 없이 생성되는 사용자를 위한 기본 생성 메서드입니다.
    public static User create(String email, String nickname, String role) {
        User user = new User();
        user.setEmail(email);
        user.setNickname(nickname);
        user.setRole(role);
        return user;
    }

    // 이메일과 비밀번호를 사용하는 로컬 가입 사용자를 생성합니다.
    public static User createLocal(String email, String password, String nickname) {
        User user = create(email, nickname, "USER");
        user.setPassword(password);
        user.setProvider("LOCAL");
        return user;
    }
}
