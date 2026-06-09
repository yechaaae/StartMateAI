package com.kakao.backend.aichat.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(AiChatProperties.class)
public class AiChatRabbitConfiguration {

    @Bean
    public Queue aiChatRequestQueue(AiChatProperties properties) {
        return new Queue(properties.requestQueue(), true);
    }

    @Bean
    public Queue aiChatResponseQueue(AiChatProperties properties) {
        return new Queue(properties.responseQueue(), true);
    }

    @Bean
    public MessageConverter jacksonMessageConverter() {
        return new JacksonJsonMessageConverter();
    }
}
