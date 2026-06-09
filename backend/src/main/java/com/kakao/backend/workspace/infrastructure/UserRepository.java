package com.kakao.backend.workspace.infrastructure;

import com.kakao.backend.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, Long> {
}
