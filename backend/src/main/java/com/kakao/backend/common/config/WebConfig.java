package com.kakao.backend.common.config;

import com.kakao.backend.common.presentation.LoginRequiredInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
// 전역 웹 설정으로 로그인 검사 인터셉터와 CORS 정책을 등록합니다.
public class WebConfig implements WebMvcConfigurer {

    private final LoginRequiredInterceptor loginRequiredInterceptor;

    // 인증 API를 제외한 모든 API 요청에 로그인 검사를 적용합니다.
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(loginRequiredInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns("/auth/**");
    }

    // 프론트 개발 서버가 세션 쿠키를 포함해 API를 호출할 수 있도록 허용합니다.
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns(
                        "http://localhost:*",
                        "http://127.0.0.1:*")
                .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
