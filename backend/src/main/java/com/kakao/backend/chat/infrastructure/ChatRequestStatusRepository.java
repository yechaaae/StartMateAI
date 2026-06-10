package com.kakao.backend.chat.infrastructure;

import com.kakao.backend.chat.domain.ChatRequestStatus;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatRequestStatusRepository extends JpaRepository<ChatRequestStatus, Long> {

    Optional<ChatRequestStatus> findByRequestId(String requestId);
}
