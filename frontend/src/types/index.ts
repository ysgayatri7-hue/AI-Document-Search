export type User={id:string;email:string;display_name:string;created_at:string}
export type Document={id:string;filename:string;size_bytes:number;page_count:number|null;status:'processing'|'indexed'|'failed';error_message:string|null;progress:number;created_at:string}
export type Citation={id:string;number:number;document_id:string;filename:string;page_number:number;excerpt:string;valid:boolean}
export type Claim={id:string;text:string;status:'supported'|'partially_supported'|'contradicted'|'unsupported';evidence_citation_ids:string[];rationale:string}
export type QueryResult={id:string;question:string;status:string;created_at:string;retrieval_latency_ms:number;total_latency_ms:number;answer:null|{id:string;text:string;mode:string;insufficient_evidence:boolean;limitations:string[];citations:Citation[];claims:Claim[]}}
export type Analytics={documents:number;indexed_documents:number;questions:number;claims_verified:number;supported_claims:number;median_latency_ms:number|null;evaluation:null|Record<string,number>}

