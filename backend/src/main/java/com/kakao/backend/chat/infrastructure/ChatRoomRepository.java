package com.kakao.backend.chat.infrastructure;

import com.kakao.backend.chat.domain.ChatRoom;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatRoomRepository extends JpaRepository<ChatRoom, Long> {

    boolean existsByIdAndWorkspaceUserId(Long roomId, Long userId);

    Optional<ChatRoom> findFirstByWorkspaceUserIdAndRoomTypeOrderByIdAsc(Long userId, String roomType);

    Optional<ChatRoom> findFirstByWorkspaceUserIdAndRoomTypeOrderByIdDesc(Long userId, String roomType);

    List<ChatRoom> findByWorkspaceUserIdAndRoomTypeOrderByIdDesc(Long userId, String roomType);
}
