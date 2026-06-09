package com.kakao.backend.chat.domain;

import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.common.domain.BaseCreatedEntity;
import com.kakao.backend.user.model.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "chat_message")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatMessage extends BaseCreatedEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "chat_room_id", nullable = false)
    private ChatRoom chatRoom;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "agent_id")
    private Agent agent;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    @Column(name = "sender_type", nullable = false)
    private String senderType;

    @Lob
    @Column(name = "content", nullable = false, columnDefinition = "text")
    private String content;

    @Column(name = "metadata", columnDefinition = "json")
    private String metadata;

    public static ChatMessage userMessage(ChatRoom chatRoom, User user, String content, String metadata) {
        ChatMessage message = new ChatMessage();
        message.setChatRoom(chatRoom);
        message.setUser(user);
        message.setSenderType("USER");
        message.setContent(content);
        message.setMetadata(metadata);
        return message;
    }

    public static ChatMessage agentMessage(ChatRoom chatRoom, Agent agent, String content, String metadata) {
        ChatMessage message = new ChatMessage();
        message.setChatRoom(chatRoom);
        message.setAgent(agent);
        message.setSenderType("AGENT");
        message.setContent(content);
        message.setMetadata(metadata);
        return message;
    }
}
