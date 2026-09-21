# 画面要件定義・サイトマップ (Pages)

フロントエンドが提供する各画面のルート構造と、対応する詳細要件定義書へのリンク一覧です。

---

## 1. サイトマップ・要件一覧

| ルート | 画面名・機能 | 対象ユーザー | 仕様書 |
| :--- | :--- | :--- | :--- |
| `/` | ルート（OAuth転送 / トップ） | 全員 | [pages/index.md](./pages/index.md) |
| `/login` | ログイン（Discord 認証） | 未ログイン | [pages/login/index.md](./pages/login/index.md) |
| `/contact` | お問い合わせフォーム | 全員 | [pages/contact/index.md](./pages/contact/index.md) |
| `/non-member` | 対象外案内 | 入会対象外者 | [pages/non-member/index.md](./pages/non-member/index.md) |
| `/profile` | プロフィール確認・編集 | 認証済みメンバー | [pages/profile/index.md](./pages/profile/index.md) |
| `/roles` | ロール確認・マニフェスト管理 | メンバー / 管理者 | [pages/roles/index.md](./pages/roles/index.md)<br>・[一般メンバー表示](./pages/roles/member-view.md)<br>・[管理者表示](./pages/roles/admin-view.md) |
| `/members` | 会員管理・入会費照合 | 管理者 | [pages/members/index.md](./pages/members/index.md) |
| `/join` | 入会案内トップ | 入会希望者 | [pages/join/index.md](./pages/join/index.md) |
| `/join/form` | 仮入会フォーム区分選択 | 入会希望者 | [pages/join/form/index.md](./pages/join/form/index.md) |
| `├─ /aoyama-student` | 青学在学生向け仮入会 | 在学生 | [pages/join/form/aoyama-student/index.md](./pages/join/form/aoyama-student/index.md) |
| `├─ /prospective-student` | 入学見込み向け仮入会 | 新入生・見込み生 | [pages/join/form/prospective-student/index.md](./pages/join/form/prospective-student/index.md) |
| `└─ /other` | 対象外向け案内 | その他 | [pages/join/form/other/index.md](./pages/join/form/other/index.md) |
| `/join/member` | 本入会申請フォーム（5ステップ） | 仮入会済みメンバー | [pages/join/member/index.md](./pages/join/member/index.md) |

---

## 2. ルーティング構造ツリー

```text
/
├─ / : コード付きアクセス時は /auth/callback へ転送する入口
├─ /login : Discord ログイン開始画面。認証失敗時の案内も表示
├─ /contact : 問い合わせフォーム。Discord チャンネルへの通知連携
├─ /non-member : 入会対象外向け案内ページ。問い合わせや仮入会へ誘導
├─ /profile : メンバー向けプロフィール編集ページ。未認証時はログインへ
├─ /roles : ロール管理ページ。member は自分の権限、admin は編集画面
├─ /members : 仮入会者一覧と入会費清算の管理ページ（管理者限定）
└─ /join : 入会案内の起点ページ。仮入会、本入会、問い合わせへ分岐
	├─ /join/form : 入会区分の選択ページ。在学生・入学見込み・その他を案内
	│  ├─ /join/form/aoyama-student : 在学生向け仮入会フォーム。学生番号からメール補完
	│  ├─ /join/form/prospective-student : 入学見込み向け仮入会フォーム。メール認証で申請
	│  └─ /join/form/other : 対象外向け案内ページ。条件説明と連絡先を表示
	└─ /join/member : 本入会フォーム。5 ステップで詳細情報と認証を進める
```

