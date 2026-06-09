package com.kakao.backend.chat.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.workspace.domain.Workspace;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
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
@Table(name = "chat_room")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatRoom extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @Column(name = "room_type", nullable = false)
    private String roomType;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "target_feature")
    private String targetFeature;

    @OneToMany(mappedBy = "chatRoom", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ChatMessage> messages = new ArrayList<>();

    @OneToMany(mappedBy = "chatRoom", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ChatAgentParticipant> participants = new ArrayList<>();

    public static ChatRoom create(Workspace workspace, String title, String roomType, String targetFeature) {
        ChatRoom room = new ChatRoom();
        room.setWorkspace(workspace);
        room.setTitle(title);
        room.setRoomType(roomType);
        room.setTargetFeature(targetFeature);
        return room;
    }
}
