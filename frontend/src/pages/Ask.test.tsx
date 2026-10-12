import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {AskPage} from './Ask'
import type {Document} from '../types'
import {api} from '../services/api'

vi.mock('../services/api',()=>({api:{ask:vi.fn(),feedback:vi.fn()}}))

const indexed:Document={id:'doc-1',filename:'policy.pdf',size_bytes:100,page_count:2,status:'indexed',error_message:null,progress:100,created_at:new Date().toISOString()}

describe('AskPage',()=>{
  beforeEach(()=>vi.clearAllMocks())
  it('prevents questions when there are no indexed sources',async()=>{
    const notice=vi.fn()
    render(<AskPage docs={[]} notice={notice} onAsked={vi.fn()}/>)
    expect(screen.getByRole('button',{name:/search documents/i})).toBeDisabled()
    expect(screen.getByText(/upload an indexed pdf first/i)).toBeInTheDocument()
  })
  it('supports accessible source selection and question validation',async()=>{
    const notice=vi.fn()
    render(<AskPage docs={[indexed]} notice={notice} onAsked={vi.fn()}/>)
    const source=screen.getByRole('button',{name:'policy.pdf'})
    expect(source).toHaveAttribute('aria-pressed','false')
    await userEvent.click(source)
    expect(source).toHaveAttribute('aria-pressed','true')
    await userEvent.click(screen.getByRole('button',{name:/search documents/i}))
    expect(notice).toHaveBeenCalledWith('Enter a question of at least 3 characters.')
  })
  it('submits a question and expands its cited evidence',async()=>{
    vi.mocked(api.ask).mockResolvedValue({id:'query-1',question:'When?',status:'completed',created_at:new Date().toISOString(),retrieval_latency_ms:10,total_latency_ms:20,answer:{id:'answer-1',text:'The launch was in 2024. [1]',mode:'extractive',insufficient_evidence:false,limitations:[],claims:[{id:'claim-1',text:'The launch was in 2024.',status:'supported',evidence_citation_ids:['citation-1'],rationale:'Supported by cited passage.'}],citations:[{id:'citation-1',number:1,document_id:'doc-1',filename:'policy.pdf',page_number:2,excerpt:'The program launched in 2024.',valid:true}]}})
    render(<AskPage docs={[indexed]} notice={vi.fn()} onAsked={vi.fn()}/>)
    await userEvent.type(screen.getByLabelText('Question'),'When did it launch?')
    await userEvent.click(screen.getByRole('button',{name:/search documents/i}))
    expect(await screen.findByText('The launch was in 2024. [1]')).toBeInTheDocument()
    const citation=screen.getByRole('button',{name:/page 2/i})
    expect(citation).toHaveAttribute('aria-expanded','false')
    await userEvent.click(citation)
    expect(citation).toHaveAttribute('aria-expanded','true')
    expect(screen.getByText('The program launched in 2024.')).toBeInTheDocument()
  })
})
