package com.kakao.backend.user.repository;

import com.kakao.backend.user.model.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

// 사용자 엔티티를 조회하고 저장하는 JPA repository입니다.
public interface UserRepository extends JpaRepository<User, Long> {

    boolean existsByEmail(String email);

    Optional<User> findByEmail(String email);
}
