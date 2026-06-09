package com.kakao.backend.chat.infrastructure;

import com.kakao.backend.chat.domain.ChatRoom;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatRoomRepository extends JpaRepository<ChatRoom, Long> {

    Optional<ChatRoom> findFirstByWorkspaceUserIdAndRoomTypeOrderByIdAsc(Long userId, String roomType);
}
