FROM node:18-alpine

WORKDIR /app

# Copy the entire workspace to resolve sibling project dependencies (TypeScript client)
COPY . .

WORKDIR /app/DEV_CORE/Web

RUN npm install

# Build Next.js
RUN npm run build

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "start"]
