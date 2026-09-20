#!/usr/bin/env python3
"""Bounded, read-only GGUF probe with the bundled Intel runtime and private logs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'maatos'
RESOURCES=ROOT/'build/macos/payload/Applications/MAAT RPG.app/Contents/Resources'
sys.path.insert(0,str(GAME))


def settings(path, adapter='llama', arch='x86_64'):
    if adapter == 'llama_intel':
        from shared.core.intel_gguf_backend import automatic_settings
    else:
        from shared.core.hardware_profile import automatic_settings
    return automatic_settings(dict(system='Darwin',machine=arch,logical=10 if arch == 'arm64' else 8,
        physical=4,gpu=arch == 'arm64',backend_info='MTL : EMBED_LIBRARY = 1' if arch == 'arm64' else 'CPU'),path)


def child(args):
    import faulthandler
    import platform
    import resource
    from contextlib import ExitStack
    from unittest.mock import patch
    faulthandler.enable()
    started=time.monotonic()
    def record(stage,**data):
        print(json.dumps(dict(stage=stage,seconds=round(time.monotonic()-started,3),
                              peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**data)),flush=True)
    from llama_cpp import _internals, llama_cpp
    from shared.core.backend_router import load_backend
    record('runtime',architecture=platform.machine(),cpu_variant=os.environ.get('MAAT_CPU_VARIANT'),
           backend=llama_cpp.llama_print_system_info().decode(),context=args.context)
    def timed(original,name):
        def call(self,*a,**kw):
            record(name+'_begin')
            result=original(self,*a,**kw)
            record(name+'_end')
            return result
        return call
    conf=settings(args.model,args.adapter,args.arch)
    with ExitStack() as stack:
        for cls,name in ((_internals.LlamaModel,'weights'),(_internals.LlamaContext,'context')):
            stack.enter_context(patch.object(cls,'__init__',timed(cls.__init__,name)))
        model=load_backend(str(args.model),backend=args.adapter,max_ctx=args.context,n_threads=conf['threads'],n_gpu_layers=conf['gpu_layers'],
                           load_options=conf['options'],allow_cpu_fallback=False)
    record('ready',adapter=model['backend'],settings=model.get('load_settings',{}))
    try:
        count=0
        if args.chat:
            from shared.core.backend_router import stream_chat
            chunks=stream_chat(model,[{'role':'system','content':'You are MAAT, a helpful companion. Answer briefly in English.'},
                                     {'role':'user','content':'Say hello in one sentence.'}],
                               {'max_tokens':16,'temperature':0})
        else:
            chunks=(c['choices'][0].get('text','') for c in model['instance'].create_completion(
                prompt='A short greeting:',max_tokens=4,temperature=0,stream=True))
        for text in chunks:
            if text:
                if not count:record('first_token')
                count+=1
        record('generation_done',chunks=count)
        if not count:raise RuntimeError('No text streamed')
    finally:
        model['instance'].close()
        record('closed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--context',type=int,default=20000)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--adapter',choices=['llama','llama_intel'],default='llama')
    parser.add_argument('--arch',choices=['x86_64','arm64'],default='x86_64')
    parser.add_argument('--chat',action='store_true')
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.child:return child(args)
    from shared.core.model_safety import system_memory,estimate_model_memory,GIB
    memory=system_memory()
    estimate=estimate_model_memory(args.model,args.context,settings(args.model,args.adapter,args.arch)['options'])
    if memory is None or memory['available']<estimate['estimated']+2*GIB:
        print(json.dumps(dict(result='not_started',reason='Test requires estimated RAM plus 2 GiB free reserve',memory=memory,estimate=estimate)))
        return 75
    out=ROOT/'build/macos/test-results';out.mkdir(exist_ok=True,parents=True)
    prefix=out/(f'{args.adapter}-{args.arch}-{args.model.stem}-chat-ctx{args.context}' if args.chat
                else f'{args.adapter}-8b-intel-ctx{args.context}')
    env=dict(os.environ,PYTHONPATH=str(RESOURCES/'runtimes/common'),PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    env.pop('LLAMA_CPP_LIB_PATH',None);env.pop('MAAT_CPU_VARIANT',None)
    started=time.monotonic();reason=None;minimum=memory['available']
    with Path(str(prefix)+'.jsonl').open('w') as stdout, Path(str(prefix)+'.stderr.log').open('w') as stderr:
        command=[str(RESOURCES/f'runtimes/{args.arch}/bin/python3.11'),'-u',__file__,str(args.model),
                 '--context',str(args.context),'--adapter',args.adapter,'--arch',args.arch,'--child']
        if args.chat:command.append('--chat')
        process=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=stderr,text=True)
        def read():
            for line in process.stdout:
                stdout.write(line);stdout.flush();print(line.rstrip(),flush=True)
        reader=threading.Thread(target=read,daemon=True);reader.start()
        try:
            while process.poll() is None:
                current=system_memory()
                if current:minimum=min(minimum,current['available'])
                if current is None or current['available']<2*GIB:reason='memory_reserve';break
                if time.monotonic()-started>args.seconds:reason='timeout';break
                time.sleep(.25)
        finally:
            if process.poll() is None:process.kill()
            code=process.wait();reader.join(timeout=3);process.stdout.close()
    report=dict(result='passed' if code==0 and not reason else 'stopped',reason=reason,exit_code=code,
                elapsed=round(time.monotonic()-started,3),minimum_available=minimum,estimate=estimate,
                adapter=args.adapter,model=args.model.name,chat_stream_tested=args.chat,
                execution='native Apple Silicon' if args.arch == 'arm64' else 'bundled x86_64 under Rosetta; not an Intel hardware benchmark')
    Path(str(prefix)+'.summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['result']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
