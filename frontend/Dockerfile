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

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "5173"]
