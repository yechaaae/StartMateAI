package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.workspace.domain.Workspace;
import org.junit.jupiter.api.Test;

class ChatCandidateAgentResolverTest {

    private final ChatCandidateAgentResolver resolver = new ChatCandidateAgentResolver();

    @Test
    void returnsRequestedAgentsWhenProvided() {
        ChatRoom room = ChatRoom.create(Workspace.create("workspace", "ACTIVE"), "room", "FEATURE_DISCUSSION", "ITEM");

        assertThat(resolver.resolve("FEATURE_CHAT", room, java.util.List.of("IdeaAgent", "FinanceAgent", "IdeaAgent")))
                .containsExactly("IdeaAgent", "FinanceAgent");
    }

    @Test
    void returnsBroadDefaultsForFreeChat() {
        ChatRoom room = ChatRoom.create(Workspace.create("workspace", "ACTIVE"), "room", "FREE_DISCUSSION", null);

        assertThat(resolver.resolve("FREE_CHAT", room, java.util.List.of()))
                .containsExactly(
                        "ProfileAgent",
                        "IdeaAgent",
                        "FinanceAgent",
                        "PolicyAgent",
                        "PlanAgent",
                        "OperationAgent",
                        "MarketingAgent"
                );
    }

    @Test
    void returnsFeatureSpecificDefaultsForItemChat() {
        ChatRoom room = ChatRoom.create(Workspace.create("workspace", "ACTIVE"), "room", "FEATURE_DISCUSSION", "ITEM");

        assertThat(resolver.resolve("FEATURE_CHAT", room, java.util.List.of()))
                .containsExactly("IdeaAgent", "ProfileAgent", "FinanceAgent");
    }
}
