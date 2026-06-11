package com.kakao.backend.workspace.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.aichat.dto.AiChatResultPayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.SavedResult;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.SavedResultRepository;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class SavedResultServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Mock
    private SavedResultRepository savedResultRepository;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private UserRepository userRepository;

    @Test
    void returnsLatestResultBySourceFeature() throws Exception {
        SavedResultService service = service();
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);
        SavedResult savedResult = SavedResult.create(
                workspace,
                "item",
                "IDEA_REPORT",
                null,
                "아이템 리포트",
                "summary",
                objectMapper.writeValueAsString(Map.of("reportData", Map.of("location", "서울")))
        );
        savedResult.setId(10L);

        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(savedResultRepository.findFirstByWorkspaceUserIdAndSourceFeatureIgnoreCaseOrderByCreatedAtDesc(2L, "item"))
                .thenReturn(Optional.of(savedResult));

        var latest = service.getLatestResult(2L, "ITEM");

        assertThat(latest).isPresent();
        assertThat(latest.get().id()).isEqualTo(10L);
        assertThat(latest.get().payload()).containsKey("reportData");
    }

    @Test
    void savesAiResultAsNewSavedResultVersion() throws Exception {
        SavedResultService service = service();
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);
        ChatRoom room = ChatRoom.create(workspace, "item room", "FEATURE", "ITEM");
        room.setId(20L);
        ChatMessage message = ChatMessage.agentMessage(room, null, "summary", null);
        message.setId(30L);
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-1",
                20L,
                "selective_collaboration",
                "OrchestratorAgent",
                "summary",
                Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null
        );
        AiChatResultPayload result = new AiChatResultPayload(
                "ITEM",
                "IDEA_REPORT",
                "아이템 리포트",
                true,
                "item-report",
                20L,
                Map.of(
                        "featureId", "item",
                        "reportData", Map.of("location", "서울"),
                        "agentSummary", "Agent summary"
                )
        );
        when(savedResultRepository.save(any(SavedResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.saveAiResult(room, response, message, result);

        ArgumentCaptor<SavedResult> captor = ArgumentCaptor.forClass(SavedResult.class);
        verify(savedResultRepository).save(captor.capture());
        SavedResult savedResult = captor.getValue();
        assertThat(savedResult.getSourceFeature()).isEqualTo("item");
        assertThat(savedResult.getResultType()).isEqualTo("IDEA_REPORT");
        Map<String, Object> payload = objectMapper.readValue(savedResult.getPayload(), new TypeReference<>() {
        });
        assertThat(payload.get("generationSource")).isEqualTo("ai_auto");
        assertThat(payload.get("requestId")).isEqualTo("req-1");
        assertThat(payload.get("roomId")).isEqualTo(20);
        assertThat(payload.get("messageId")).isEqualTo(30);
        assertThat(payload.get("reportData")).isInstanceOf(Map.class);
    }

    private SavedResultService service() {
        return new SavedResultService(savedResultRepository, workspaceRepository, userRepository, objectMapper);
    }
}
