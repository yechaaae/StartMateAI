package com.kakao.backend.chat.infrastructure;

import com.kakao.backend.chat.domain.ChatMessage;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    List<ChatMessage> findTop20ByChatRoomIdOrderByIdDesc(Long chatRoomId);

    List<ChatMessage> findByChatRoomIdOrderByIdAsc(Long chatRoomId);
}
