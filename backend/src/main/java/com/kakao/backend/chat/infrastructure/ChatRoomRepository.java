package com.kakao.backend.chat.infrastructure;

import com.kakao.backend.domain.ChatRoom;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatRoomRepository extends JpaRepository<ChatRoom, Long> {

    List<ChatRoom> findByWorkspaceIdOrderByCreatedAtAsc(Long workspaceId);
}
