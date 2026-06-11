export const loginFields = [
  {
    name: 'email',
    label: '이메일',
    type: 'email',
    placeholder: 'startmate@example.com',
    autoComplete: 'email',
  },
  {
    name: 'password',
    label: '비밀번호',
    type: 'password',
    placeholder: '비밀번호',
    autoComplete: 'off',
    ignorePasswordManagers: true,
  },
]

export const signupFields = [
  {
    name: 'email',
    label: '이메일',
    type: 'email',
    placeholder: 'startmate@example.com',
    autoComplete: 'email',
  },
  {
    name: 'nickname',
    label: '닉네임',
    type: 'text',
    placeholder: '민서',
    autoComplete: 'nickname',
  },
  {
    name: 'password',
    label: '비밀번호',
    type: 'password',
    placeholder: '6자 이상',
    autoComplete: 'off',
    ignorePasswordManagers: true,
  },
  {
    name: 'passwordConfirm',
    label: '비밀번호 확인',
    type: 'password',
    placeholder: '비밀번호를 한 번 더 입력',
    autoComplete: 'off',
    ignorePasswordManagers: true,
    revealWithPrevious: true,
  },
]
