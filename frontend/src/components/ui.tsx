import type {ButtonHTMLAttributes,HTMLAttributes,ReactNode} from 'react'
import {LoaderCircle,X} from 'lucide-react'
export function Button({className='',loading,children,...props}:ButtonHTMLAttributes<HTMLButtonElement>&{loading?:boolean}){return <button className={`button ${className}`} disabled={loading||props.disabled} {...props}>{loading&&<LoaderCircle size={16} className="spin"/>}{children}</button>}
export function Card({className='',...props}:HTMLAttributes<HTMLDivElement>){return <div className={`card ${className}`} {...props}/>}
export function Badge({tone='neutral',children}:{tone?:string;children:ReactNode}){return <span className={`badge ${tone}`}>{children}</span>}
export function Empty({icon,title,body,action}:{icon:ReactNode;title:string;body:string;action?:ReactNode}){return <div className="empty"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{body}</p>{action}</div>}
export function Toast({message,onClose}:{message:string;onClose:()=>void}){return <div className="toast" role="status">{message}<button aria-label="Dismiss" onClick={onClose}><X size={16}/></button></div>}
export function PageSkeleton(){return <div className="page-skeleton" aria-label="Loading workspace"><div className="skeleton-title"/><div className="skeleton-command"/><div className="skeleton-grid">{[1,2,3,4].map(x=><div key={x}/>)}</div><div className="skeleton-panel"/></div>}

