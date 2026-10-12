import type {Analytics,Document,QueryResult,User} from '../types'
const BASE=import.meta.env.VITE_API_URL||''
let token=localStorage.getItem('ai_document_search_token')||localStorage.getItem('verity_token')||''
if(token){localStorage.setItem('ai_document_search_token',token);localStorage.removeItem('verity_token')}
export const setToken=(value:string)=>{token=value;value?localStorage.setItem('ai_document_search_token',value):localStorage.removeItem('ai_document_search_token')}
async function request<T>(path:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers); if(token)headers.set('Authorization',`Bearer ${token}`); if(!(options.body instanceof FormData))headers.set('Content-Type','application/json')
 const response=await fetch(`${BASE}${path}`,{...options,headers}); if(response.status===401&&token){setToken('');window.dispatchEvent(new Event('ai-document-search:session-expired'))}if(!response.ok){let message=`Request failed (${response.status})`;try{message=(await response.json()).detail||message}catch{}throw new Error(message)}
 return response.status===204?undefined as T:response.json()
}
async function preview(id:string){const response=await fetch(`${BASE}/api/documents/${id}/content`,{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error(response.status===401?'Your session has expired.':'Preview could not be opened.');const blob=await response.blob();const url=URL.createObjectURL(blob);window.open(url,'_blank','noopener,noreferrer');setTimeout(()=>URL.revokeObjectURL(url),60000)}
export const api={
 me:()=>request<User>('/api/auth/me'),
 login:(email:string,password:string)=>request<{access_token:string;user:User}>('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})}),
 register:(email:string,display_name:string,password:string)=>request<{access_token:string;user:User}>('/api/auth/register',{method:'POST',body:JSON.stringify({email,display_name,password})}),
 documents:()=>request<Document[]>('/api/documents'),
 upload:(file:File)=>{const body=new FormData();body.append('file',file);return request<Document>('/api/documents',{method:'POST',body})},
 remove:(id:string)=>request<void>(`/api/documents/${id}`,{method:'DELETE'}), retry:(id:string)=>request<Document>(`/api/documents/${id}/retry`,{method:'POST'}),preview,
 ask:(question:string,document_ids:string[])=>request<QueryResult>('/api/query',{method:'POST',body:JSON.stringify({question,document_ids})}),
 history:()=>request<QueryResult[]>('/api/history'), analytics:()=>request<Analytics>('/api/analytics/overview'),
 verification:()=>request<{live:Record<string,number>;offline_evaluation:null|Record<string,number>}>('/api/analytics/verification'),
 feedback:(answer_id:string,helpful:boolean)=>request('/api/feedback',{method:'POST',body:JSON.stringify({answer_id,helpful})})
}

