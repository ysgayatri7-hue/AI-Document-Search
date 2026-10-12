import {useState} from 'react'
import {motion} from 'framer-motion'
import {BookOpen,CheckCircle2,ChevronDown,ChevronUp,Clipboard,MessageSquareText,Send,ThumbsDown,ThumbsUp,TriangleAlert} from 'lucide-react'
import {api} from '../services/api'
import type {Document,QueryResult} from '../types'
import {Badge,Button,Card,Empty} from '../components/ui'

const examples=['What are the document’s main conclusions?','Which risks and limitations are identified?','Summarize the key dates and obligations.']

export function AskPage({docs,notice,onAsked}:{docs:Document[];notice:(message:string)=>void;onAsked:()=>void}) {
  const [question,setQuestion]=useState('')
  const [selected,setSelected]=useState<string[]>([])
  const [busy,setBusy]=useState(false)
  const [result,setResult]=useState<QueryResult|null>(null)
  const [open,setOpen]=useState<string|null>(null)
  const indexed=docs.filter(document=>document.status==='indexed')

  async function ask(){
    if(!indexed.length){notice('Upload and index a PDF before asking a question.');return}
    if(question.trim().length<3){notice('Enter a question of at least 3 characters.');return}
    setBusy(true)
    try{setResult(await api.ask(question.trim(),selected));onAsked()}catch(error){notice((error as Error).message)}finally{setBusy(false)}
  }
  async function feedback(helpful:boolean){
    if(!result?.answer)return
    try{await api.feedback(result.answer.id,helpful);notice('Thanks—your feedback was recorded.')}catch(error){notice((error as Error).message)}
  }
  async function copyAnswer(){
    if(!result?.answer)return
    try{await navigator.clipboard.writeText(result.answer.text);notice('Answer copied.')}catch{notice('Copy failed. Select the answer text and copy it manually.')}
  }

  return <div className="page-stack ask-page">
    <div className="page-heading"><div><p className="eyebrow">Grounded intelligence</p><h1>Ask your documents</h1><p>Every answer is traceable to a page and passage.</p></div></div>
    <Card className="composer"><textarea aria-label="Question" placeholder="Ask a precise question about your documents…" value={question} onChange={event=>setQuestion(event.target.value)} onKeyDown={event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter')void ask()}}/><div className="composer-foot"><div className="source-picker"><BookOpen size={16}/><span>{selected.length?`${selected.length} source${selected.length>1?'s':''} selected`:'All indexed documents'}</span></div><Button className="primary" loading={busy} disabled={!indexed.length} onClick={ask}><Send size={16}/>Search documents</Button></div></Card>
    {indexed.length>0&&<div className="filter-chips" aria-label="Document filters">{indexed.map(document=>{const active=selected.includes(document.id);return <button key={document.id} className={active?'chip active':'chip'} aria-pressed={active} onClick={()=>setSelected(active?selected.filter(id=>id!==document.id):[...selected,document.id])}>{document.filename}</button>})}</div>}
    {!result&&!busy&&<><div className="suggestions">{examples.map(example=><button key={example} onClick={()=>setQuestion(example)}>{example}</button>)}</div>{indexed.length===0&&<Empty icon={<BookOpen/>} title="Upload an indexed PDF first" body="Questions require evidence from at least one successfully processed document."/>}</>}
    {busy&&<Card className="answer-skeleton" role="status"><div/><div/><div/><span>Retrieving, reranking, and checking claims…</span></Card>}
    {result?.answer&&<motion.div className="answer-grid" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}}><Card className="answer-card"><div className="answer-head"><div className="answer-avatar">AI</div><div><span className="eyebrow">DOCUMENT ANSWER</span><small>{result.answer.mode} mode · {(result.total_latency_ms/1000).toFixed(2)}s</small></div></div>{result.answer.insufficient_evidence?<div className="insufficient"><TriangleAlert/><div><h3>Insufficient evidence</h3><p>{result.answer.text}</p></div></div>:<p className="answer-text">{result.answer.text}</p>}<div className="claim-list"><h3>Claim verification</h3>{result.answer.claims.map(claim=><div className="claim" key={claim.id}><Badge tone={claim.status}>{claim.status==='supported'?<CheckCircle2 size={13}/>:<TriangleAlert size={13}/>} {claim.status.replace('_',' ')}</Badge><div><p>{claim.text}</p><small>{claim.rationale}</small></div></div>)}</div>{result.answer.limitations.map(limitation=><p className="limitation" key={limitation}><TriangleAlert size={14}/>{limitation}</p>)}<div className="answer-actions"><button onClick={copyAnswer}><Clipboard size={16}/>Copy</button><span>Was this helpful?</span><button aria-label="Helpful" onClick={()=>feedback(true)}><ThumbsUp size={16}/></button><button aria-label="Not helpful" onClick={()=>feedback(false)}><ThumbsDown size={16}/></button></div></Card><aside className="evidence"><div className="evidence-title"><div><p className="eyebrow">Evidence</p><h2>{result.answer.citations.length} source passages</h2></div><MessageSquareText/></div>{result.answer.citations.map(citation=><Card key={citation.id} className="evidence-card"><button aria-expanded={open===citation.id} onClick={()=>setOpen(open===citation.id?null:citation.id)}><span className="citation-num">{citation.number}</span><div><strong>{citation.filename}</strong><small>Page {citation.page_number} · {citation.valid?'Citation validated':'Validation failed'}</small></div>{open===citation.id?<ChevronUp/>:<ChevronDown/>}</button>{open===citation.id&&<p>{citation.excerpt}</p>}</Card>)}</aside></motion.div>}
  </div>
}
