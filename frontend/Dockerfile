FROM node:24-alpine

WORKDIR /app

# 非root実行を前提に、作業ディレクトリをnodeユーザーへ付与
RUN chown -R node:node /app
USER node

# パッケージインストールをキャッシュ
COPY --chown=node:node package*.json ./
RUN npm ci

# アプリ本体をコピー
COPY --chown=node:node . .

# 開発サーバーの起動コマンド（ホットリロード有効）
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "5173"]
