import { defineConfig,loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig(({mode})=>{const env=loadEnv(mode,'.','');return {plugins:[react()],server:{port:5173,proxy:{'/api':env.VITE_PROXY_TARGET||'http://localhost:8000'}},build:{rolldownOptions:{output:{manualChunks:(id:string)=>id.includes('/recharts/')?'charts':id.includes('/framer-motion/')?'motion':id.includes('/react-dom/')||id.includes('/react/')?'react':undefined}}},test:{environment:'jsdom',setupFiles:['./src/test/setup.ts']}}})

