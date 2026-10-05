#!/usr/bin/env python3
"""Compile Cygma semantic design tokens to native app formats; stdlib only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
 'surface.canvas':'background','surface.panel':'surface','surface.raised':'elevated',
 'surface.hover':'elevated','surface.selection':'elevated',
 'text.primary':'text','text.secondary':'muted','text.muted':'muted','text.selected':'text',
 'text.inverse':'on_accent','action.primary':'accent','action.hover':'accent','action.onPrimary':'on_accent',
 'border.subtle':'border','border.control':'control_border','border.focus':'accent',
 'state.success':'success','state.warning':'warning','state.error':'error','state.info':'info',
 'syntax.keyword':'violet','syntax.string':'success','syntax.function':'accent',
 'syntax.type':'info','syntax.number':'rose','syntax.comment':'muted','syntax.variable':'text',
 'syntax.operator':'secondary','syntax.constant':'warning',
}
ANSI_ROLES = ['muted','error','success','warning','info','violet','secondary','text',
              'muted','error','success','warning','info','rose','accent','text']
SURFACES = ('surface.canvas','surface.panel','surface.raised','surface.hover','surface.selection')


def dumps(data):
    return json.dumps(data,indent=2,ensure_ascii=False)+'\n'


def luminance(value):
    channels=[int(value[i:i+2],16)/255 for i in (1,3,5)]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in channels]
    return sum(x*w for x,w in zip(linear,(.2126,.7152,.0722)))


def contrast(a,b):
    lo,hi=sorted((luminance(a),luminance(b)))
    return (hi+.05)/(lo+.05)


def dtcg(theme):
    doc={'$extensions':{'audio.cygma':{'name':theme['name'],'appearance':theme['appearance'],'version':'0.1.0'}},
         '$description':theme['description'], 'base':{'$type':'color'}}
    for name,color in theme['colors'].items():
        doc['base'][name]={'$value':{'colorSpace':'srgb','components':[int(color[i:i+2],16)/255 for i in (1,3,5)],'alpha':1}}
    for role,source in {**ALIASES,**{f'terminal.ansi{i}':r for i,r in enumerate(ANSI_ROLES)}}.items():
        group,name=role.split('.')
        doc.setdefault(group,{'$type':'color'})[name]={'$value':'{base.'+source+'}'}
    return doc


def resolve(doc):
    def value(path,seen=()):
        if path in seen: raise ValueError('Cyclic token: '+path)
        node=doc
        for piece in path.split('.'): node=node[piece]
        val=node['$value']
        if isinstance(val,str):
            if not val.startswith('{') or not val.endswith('}'): raise ValueError('Invalid alias')
            return value(val[1:-1],seen+(path,))
        if val['colorSpace']!='srgb' or val.get('alpha',1)!=1: raise ValueError('Expected opaque sRGB')
        if len(val['components'])!=3 or not all(0<=c<=1 for c in val['components']): raise ValueError('Invalid sRGB')
        return '#'+''.join(f'{round(c*255):02X}' for c in val['components'])
    result={}
    for group,nodes in doc.items():
        if group.startswith('$') or group=='base':continue
        for name in nodes:
            if not name.startswith('$'):result[group+'.'+name]=value(group+'.'+name)
    return result


def audit(themes):
    pairs=[]
    for slug,theme in themes.items():
        tokens=theme['tokens']
        foregrounds=[r for r in tokens if r.startswith(('syntax.','state.','terminal.'))]
        foregrounds+=['text.primary','text.secondary','text.muted','text.selected','action.primary']
        for fg in foregrounds:
            for bg in SURFACES:
                ratio=contrast(tokens[fg],tokens[bg])
                pairs.append({'theme':slug,'foreground':fg,'background':bg,'ratio':ratio,'minimum':4.5,'pass':ratio>=4.5})
        for fg in ('border.control','border.focus'):
            for bg in SURFACES:
                ratio=contrast(tokens[fg],tokens[bg])
                pairs.append({'theme':slug,'foreground':fg,'background':bg,'ratio':ratio,'minimum':3,'pass':ratio>=3})
        for bg in ('action.primary','action.hover'):
            ratio=contrast(tokens['action.onPrimary'],tokens[bg])
            pairs.append({'theme':slug,'foreground':'action.onPrimary','background':bg,'ratio':ratio,'minimum':4.5,'pass':ratio>=4.5})
    failed=[p for p in pairs if not p['pass']]
    if failed:raise ValueError(dumps(failed))
    return {'standard':'WCAG 2.2 contrast criteria 1.4.3 and 1.4.11',
            'scope':'Named opaque foreground/background pairs only; not full application or legal conformance.',
            'count':len(pairs),'minimumTextRatio':min(p['ratio'] for p in pairs if p['minimum']==4.5),'pairs':pairs}


def vscode(theme):
    t=theme['tokens'];c={}
    def use(keys,role):
        for key in keys.split():c[key]=t[role]
    use('foreground editor.foreground terminal.foreground input.foreground dropdown.foreground list.activeSelectionForeground list.inactiveSelectionForeground list.hoverForeground sideBar.foreground statusBar.foreground statusBar.noFolderForeground activityBar.foreground tab.activeForeground tab.inactiveForeground editorWidget.foreground menu.foreground quickInput.foreground titleBar.activeForeground titleBar.inactiveForeground button.secondaryForeground editorHoverWidget.foreground','text.primary')
    use('descriptionForeground disabledForeground editorLineNumber.foreground editorCodeLens.foreground input.placeholderForeground activityBar.inactiveForeground list.deemphasizedForeground','text.muted')
    use('editor.background terminal.background','surface.canvas')
    use('sideBar.background activityBar.background statusBar.background statusBar.noFolderBackground titleBar.activeBackground titleBar.inactiveBackground tab.inactiveBackground panel.background','surface.panel')
    use('editorWidget.background editorHoverWidget.background menu.background quickInput.background input.background dropdown.background button.secondaryBackground','surface.raised')
    use('editor.selectionBackground editor.inactiveSelectionBackground list.activeSelectionBackground list.inactiveSelectionBackground list.hoverBackground editor.lineHighlightBackground tab.activeBackground button.secondaryHoverBackground','surface.selection')
    use('editor.selectionForeground','text.selected')
    use('focusBorder list.focusOutline input.border dropdown.border button.border checkbox.border editorCursor.foreground terminalCursor.foreground','border.focus')
    use('widget.border editorWidget.border editorHoverWidget.border panel.border sideBar.border statusBar.border tab.border menu.border','border.subtle')
    use('button.background badge.background activityBarBadge.background progressBar.background','action.primary')
    use('button.hoverBackground','action.hover')
    use('button.foreground badge.foreground activityBarBadge.foreground','action.onPrimary')
    use('textLink.foreground textLink.activeForeground','action.primary')
    use('errorForeground editorError.foreground gitDecoration.deletedResourceForeground','state.error')
    use('editorWarning.foreground gitDecoration.modifiedResourceForeground','state.warning')
    use('editorInfo.foreground','state.info')
    use('gitDecoration.addedResourceForeground','state.success')
    use('inputValidation.errorBackground inputValidation.warningBackground inputValidation.infoBackground','surface.raised')
    use('inputValidation.errorForeground inputValidation.warningForeground inputValidation.infoForeground','text.primary')
    use('inputValidation.errorBorder','state.error');use('inputValidation.warningBorder','state.warning');use('inputValidation.infoBorder','state.info')
    names=['Black','Red','Green','Yellow','Blue','Magenta','Cyan','White']
    for i,name in enumerate(names):
        c['terminal.ansi'+name]=t[f'terminal.ansi{i}'];c['terminal.ansiBright'+name]=t[f'terminal.ansi{i+8}']
    scopes={'comment':'comment punctuation.definition.comment','keyword':'keyword storage','string':'string',
      'function':'entity.name.function support.function','type':'entity.name.type support.type entity.name.class',
      'number':'constant.numeric','variable':'variable','operator':'keyword.operator punctuation','constant':'constant.language support.constant'}
    rules=[{'name':role.title(),'scope':scope.split(),'settings':{'foreground':t['syntax.'+role]}} for role,scope in scopes.items()]
    semantic={'parameter':'variable','property':'variable','variable':'variable','function':'function','method':'function',
              'type':'type','class':'type','interface':'type','enum':'type','enumMember':'constant','keyword':'keyword',
              'comment':'comment','string':'string','number':'number','operator':'operator'}
    return {'$schema':'vscode://schemas/color-theme','name':'Cygma '+theme['name'],'type':theme['appearance'],
            'semanticHighlighting':True,'colors':c,'tokenColors':rules,
            'semanticTokenColors':{key:t['syntax.'+role] for key,role in semantic.items()}}


def native_ports(slug,theme):
    t=theme['tokens'];name='Cygma '+theme['name'];a=[t[f'terminal.ansi{i}'] for i in range(16)]
    output={f'ports/vscode/themes/cygma-{slug}.json':dumps(vscode(theme))}
    kitty={'background':t['surface.canvas'],'foreground':t['text.primary'],'cursor':t['action.primary'],
           'cursor_text_color':t['action.onPrimary'],'selection_background':t['surface.selection'],'selection_foreground':t['text.selected'],
           **{f'color{i}':color for i,color in enumerate(a)}}
    output[f'ports/kitty/cygma-{slug}.conf']='# '+name+'; generated from semantic tokens\n'+''.join(f'{k} {v}\n' for k,v in kitty.items())
    ansi_names=['black','red','green','yellow','blue','magenta','cyan','white']
    alacritty={'primary':{'background':t['surface.canvas'],'foreground':t['text.primary']},
        'cursor':{'text':t['action.onPrimary'],'cursor':t['action.primary']},
        'selection':{'text':t['text.selected'],'background':t['surface.selection']},
        'normal':dict(zip(ansi_names,a[:8])),'bright':dict(zip(ansi_names,a[8:]))}
    output[f'ports/alacritty/cygma-{slug}.toml']='# '+name+'\n'+''.join(f'\n[colors.{group}]\n'+''.join(f'{k} = "{v}"\n' for k,v in values.items()) for group,values in alacritty.items())
    wez={'foreground':t['text.primary'],'background':t['surface.canvas'],'cursor_bg':t['action.primary'],
         'cursor_border':t['action.primary'],'cursor_fg':t['action.onPrimary'],'selection_bg':t['surface.selection'],'selection_fg':t['text.selected']}
    output[f'ports/wezterm/cygma-{slug}.toml']='[colors]\n'+''.join(f'{k} = "{v}"\n' for k,v in wez.items())+'ansi = '+json.dumps(a[:8])+'\nbrights = '+json.dumps(a[8:])+f'\n\n[metadata]\nname = "{name}"\nauthor = "Cygma Audio"\n'
    groups={'Normal':('text.primary','surface.canvas'),'NormalFloat':('text.primary','surface.raised'),
      'FloatBorder':('border.control','surface.raised'),'Comment':('syntax.comment',None),'Constant':('syntax.constant',None),
      'String':('syntax.string',None),'Number':('syntax.number',None),'Identifier':('syntax.variable',None),
      'Function':('syntax.function',None),'Statement':('syntax.keyword',None),'Type':('syntax.type',None),
      'PreProc':('syntax.keyword',None),'Special':('syntax.operator',None),'LineNr':('text.muted','surface.canvas'),
      'CursorLineNr':('action.primary','surface.canvas'),'Visual':('text.selected','surface.selection'),
      'CursorLine':(None,'surface.hover'),'Pmenu':('text.primary','surface.raised'),
      'PmenuSel':('action.onPrimary','action.primary'),'StatusLine':('text.primary','surface.panel'),
      'StatusLineNC':('text.muted','surface.panel'),'Search':('action.onPrimary','action.primary'),
      'IncSearch':('action.onPrimary','action.primary'),'DiagnosticError':('state.error',None),
      'DiagnosticWarn':('state.warning',None),'DiagnosticInfo':('state.info',None),'DiagnosticHint':('state.success',None)}
    lua=[f'-- {name}: generated semantic colours','vim.cmd("highlight clear")',
         f'vim.o.background = "{theme["appearance"]}"',f'vim.g.colors_name = "cygma_{slug}"']
    for group,(fg,bg) in groups.items():
        attrs=[]
        if fg:attrs.append('fg = "'+t[fg]+'"')
        if bg:attrs.append('bg = "'+t[bg]+'"')
        lua.append('vim.api.nvim_set_hl(0, "'+group+'", { '+', '.join(attrs)+' })')
    for i,color in enumerate(a):lua.append(f'vim.g.terminal_color_{i} = "{color}"')
    output[f'ports/neovim/colors/cygma_{slug}.lua']='\n'.join(lua)+'\n'
    definitions={'theme_bg_color':'surface.panel','theme_fg_color':'text.primary','theme_base_color':'surface.canvas',
      'theme_text_color':'text.primary','theme_selected_bg_color':'action.primary','theme_selected_fg_color':'action.onPrimary',
      'borders':'border.control','error_color':'state.error','warning_color':'state.warning','success_color':'state.success'}
    css='/* '+name+'; GTK theme, not a libadwaita override. */\n'+''.join(f'@define-color {key} {t[role]};\n' for key,role in definitions.items())
    css+='''window, dialog, .background { background-color: @theme_bg_color; color: @theme_fg_color; }
entry, textview, textview text { background-color: @theme_base_color; color: @theme_text_color; border: 1px solid @borders; }
button, combobox button { background-image: none; background-color: @theme_bg_color; color: @theme_fg_color; border: 1px solid @borders; border-radius: 6px; }
button:hover, button:active, button.suggested-action, selection { background-color: @theme_selected_bg_color; color: @theme_selected_fg_color; }
*:focus { outline: 2px solid @theme_selected_bg_color; outline-offset: 2px; }
label.error { color: @error_color; } label.warning { color: @warning_color; } label.success { color: @success_color; }
'''
    for version in ('3.0','4.0'):output[f'ports/gtk/cygma-{slug}/gtk-{version}/gtk.css']=css
    return output


def generate():
    seeds=json.loads((ROOT/'tokens/palette-source.json').read_text(encoding='utf-8'))['themes']
    outputs={};themes={}
    for slug,seed in seeds.items():
        doc=dtcg(seed);tokens=resolve(doc)
        themes[slug]={k:seed[k] for k in ('name','appearance','description')};themes[slug]['tokens']=tokens
        outputs[f'tokens/{slug}.tokens.json']=dumps(doc)
        outputs[f'site/downloads/{slug}.tokens.json']=dumps(doc)
        outputs.update(native_ports(slug,themes[slug]))
    report=audit(themes)
    outputs['reports/contrast.json']=dumps(report);outputs['site/downloads/contrast-report.json']=dumps(report)
    resolved=dumps({'version':1,'themes':themes})
    outputs['dist/themes.json']=resolved;outputs['site/themes.json']=resolved
    css='/* Generated from DTCG semantic roles. Never edit compiled files. */\n'
    for slug,theme in themes.items():
        css+=f'[data-theme="{slug}"] {{\n  color-scheme: {theme["appearance"]};\n'
        css+=''.join(f'  --{role.replace(".","-")}: {value};\n' for role,value in theme['tokens'].items())+'}\n'
    outputs['dist/tokens.css']=css;outputs['site/tokens.css']=css
    outputs['ports/vscode/package.json']=dumps({'name':'cygma-themes','displayName':'Cygma Themes','description':'Ember, Porcelain and Nocturne colour themes by Cygma Audio.',
      'version':'0.1.0','publisher':'cygma-audio','engines':{'vscode':'^1.80.0'},'categories':['Themes'],'license':'MIT',
      'contributes':{'themes':[{'label':'Cygma '+theme['name'],'uiTheme':'vs' if theme['appearance']=='light' else 'vs-dark','path':f'./themes/cygma-{slug}.json'} for slug,theme in themes.items()]}})
    outputs['ports/vscode/LICENSE']=(ROOT/'LICENSE').read_text(encoding='utf-8')
    schemes=[]
    keys=['black','red','green','yellow','blue','purple','cyan','white','brightBlack','brightRed','brightGreen','brightYellow','brightBlue','brightPurple','brightCyan','brightWhite']
    for slug,theme in themes.items():
        t=theme['tokens'];schemes.append({'name':'Cygma '+theme['name'],'background':t['surface.canvas'],'foreground':t['text.primary'],
          'cursorColor':t['action.primary'],'selectionBackground':t['surface.selection'],**{key:t[f'terminal.ansi{i}'] for i,key in enumerate(keys)}})
    outputs['ports/windows-terminal/cygma.json']=dumps({'schemes':schemes})
    tessel={'version':1,'themes':{}}
    roles={'frame':'surface.canvas','panel':'surface.panel','control':'surface.raised','plot':'surface.canvas','border':'border.subtle',
     'text':'text.primary','muted':'text.secondary','quiet':'text.muted','accent':'action.primary','highlight':'syntax.operator','cyan':'state.info',
     'mint':'state.success','amber':'state.warning','error':'state.error','on_accent':'action.onPrimary','control_border':'border.control'}
    for slug,theme in themes.items():tessel['themes'][slug]={'name':'Cygma '+theme['name'],**{key:theme['tokens'][role] for key,role in roles.items()}}
    outputs['ports/tessel/cygma.json']=dumps(tessel)
    return outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Fail if tracked exports differ; do not write.')
    args=parser.parse_args();outputs=generate();stale=[]
    for relative,contents in outputs.items():
        path=ROOT/relative
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8')!=contents:stale.append(relative)
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(contents,encoding='utf-8',newline='\n')
    if stale:raise SystemExit('Stale exports: '+', '.join(stale))
    print(f'{"Verified" if args.check else "Generated"} {len(outputs)} token and theme files. Contrast audit passed.')


if __name__=='__main__':main()
