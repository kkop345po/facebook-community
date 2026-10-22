import urllib.request,json,subprocess,sys,pathlib
root=pathlib.Path.cwd(); dest=root/'.agents'/'skills'; dest.mkdir(parents=True,exist_ok=True)
installer=r'C:\Users\GIGABYTE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py'
records=[]
for repo,prefixes in [('cloudflare/skills',['skills/']),('google/skills',['skills/cloud/','skills/developers/finding-google-skills/','skills/developers/retrieving-developer-knowledge/']),('resend/resend-skills',['skills/']),('bmad-code-org/BMAD-METHOD',['skills/'])]:
 data=json.load(urllib.request.urlopen('https://api.github.com/repos/'+repo+'/git/trees/main?recursive=1'))
 paths=[x['path'].rsplit('/',1)[0] for x in data['tree'] if x['path'].endswith('/SKILL.md') and any(x['path'].startswith(p) for p in prefixes) and (repo!='bmad-code-org/BMAD-METHOD' or x['path'].count('/')==2)]
 print('INSTALL',repo,len(paths),flush=True)
 result=subprocess.run([sys.executable,installer,'--repo',repo,'--ref',data['sha'],'--dest',str(dest),'--path',*paths])
 records.append(dict(repo=repo,commit=data['sha'],paths=paths,exit_code=result.returncode))
 if result.returncode: break
(root/'skill-install-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
