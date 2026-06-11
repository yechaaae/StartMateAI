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
                        "MarketingAgent",
                        "SimulationAgent"
                );
    }

    @Test
    void returnsFeatureSpecificDefaultsForItemChat() {
        ChatRoom room = ChatRoom.create(Workspace.create("workspace", "ACTIVE"), "room", "FEATURE_DISCUSSION", "ITEM");

        assertThat(resolver.resolve("FEATURE_CHAT", room, java.util.List.of()))
                .containsExactly("IdeaAgent", "ProfileAgent", "FinanceAgent");
    }

    @Test
    void returnsFeatureSpecificDefaultsForEachReportFeature() {
        Workspace workspace = Workspace.create("workspace", "ACTIVE");

        assertThat(resolver.resolve("FEATURE_CHAT", ChatRoom.create(workspace, "room", "FEATURE_DISCUSSION", "SIMULATOR"), java.util.List.of()))
                .containsExactly("IdeaAgent", "FinanceAgent", "SimulationAgent");
        assertThat(resolver.resolve("FEATURE_CHAT", ChatRoom.create(workspace, "room", "FEATURE_DISCUSSION", "SUPPORT"), java.util.List.of()))
                .containsExactly("ProfileAgent", "IdeaAgent", "PolicyAgent");
        assertThat(resolver.resolve("FEATURE_CHAT", ChatRoom.create(workspace, "room", "FEATURE_DISCUSSION", "PLAN"), java.util.List.of()))
                .containsExactly("ProfileAgent", "IdeaAgent", "PolicyAgent", "PlanAgent");
        assertThat(resolver.resolve("FEATURE_CHAT", ChatRoom.create(workspace, "room", "FEATURE_DISCUSSION", "OPERATION"), java.util.List.of()))
                .containsExactly("OperationAgent", "FinanceAgent", "MarketingAgent");
        assertThat(resolver.resolve("FEATURE_CHAT", ChatRoom.create(workspace, "room", "FEATURE_DISCUSSION", "SNS"), java.util.List.of()))
                .containsExactly("MarketingAgent", "OperationAgent", "ProfileAgent");
    }
}
