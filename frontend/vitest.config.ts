import { defineConfig } from 'vitest/config'

// Config separada da do Vite para não arrastar tipos de teste para o build.
export default defineConfig({
  test: {
    // Ambiente node: os testes cobrem lógica pura (parser SSE, buffer, markdown
    // via renderToStaticMarkup) e não precisam de DOM nem de jsdom.
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
})
