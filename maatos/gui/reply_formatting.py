"""Offline native Qt Markdown, with a conservative readable-math subset.

Only presentation changes. Original model text, code and memory stay untouched.
Unsupported LaTeX is kept verbatim rather than guessing at its meaning.
"""
import re
from PySide6.QtCore import QByteArray
from PySide6.QtGui import (QColor, QFontDatabase, QTextCharFormat, QTextCursor, QTextDocument,
                          QTextDocumentFragment, QTextFormat, QTextLength, QTextTable)


SYMBOLS = {
    'alpha':'α', 'beta':'β', 'gamma':'γ', 'delta':'δ', 'Delta':'Δ', 'epsilon':'ε',
    'theta':'θ', 'lambda':'λ', 'mu':'μ', 'nu':'ν', 'pi':'π', 'rho':'ρ', 'sigma':'σ',
    'Sigma':'Σ', 'phi':'φ', 'Phi':'Φ', 'psi':'ψ', 'omega':'ω', 'Omega':'Ω',
    'times':'×', 'cdot':'·', 'approx':'≈', 'neq':'≠', 'leq':'≤', 'geq':'≥',
    'le':'≤', 'ge':'≥', 'infty':'∞', 'sum':'∑', 'prod':'∏', 'int':'∫',
    'partial':'∂', 'nabla':'∇', 'pm':'±', 'to':'→', 'rightarrow':'→', 'Rightarrow':'⇒',
    'min':'min', 'max':'max', 'sin':'sin', 'cos':'cos', 'log':'log', 'ln':'ln', 'exp':'exp',
}
SUP = dict(zip('0123456789+-=()in', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ'))
SUB = dict(zip('0123456789+-=()aehijklmnoprstuvx', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ'))


def reply_text_format():
    """Explicit color prevents a reply from inheriting the user's gold text."""
    fmt = QTextCharFormat()
    fmt.setForeground(QColor('#ffffff'))
    return fmt


def readable_math(source):
    original = source.strip()
    if len(original) > 2000:
        return original
    value = original
    # Bounded iterations handle nested simple fractions without recursive parsing.
    for _ in range(12):
        before = value
        value = re.sub(r'\\(?:frac|dfrac|tfrac)\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', value)
        value = re.sub(r'\\sqrt(?:\[([2-9])\])?\{([^{}]*)\}',
                       lambda m: ('' if m[1] in (None,'2') else SUP[m[1]])+'√('+m[2]+')', value)
        value = re.sub(r'\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}', r'\1', value)
        if value == before:
            break
    value = re.sub(r'\\(?:left|right)(?=[()[\]{}|.])', '', value)
    value = re.sub(r'\\([a-zA-Z]+)', lambda m: SYMBOLS.get(m[1], m[0]), value)
    value = re.sub(r'\\[,;! ]', ' ', value)
    # Never partially rewrite an unknown command or a complex LaTeX environment.
    if '\\' in value:
        return original
    def script(m):
        content = m[2] if m[2] is not None else m[3]
        alphabet = SUP if m[1] == '^' else SUB
        return ''.join(alphabet[c] for c in content) if all(c in alphabet for c in content) else m[0]
    value = re.sub(r'([_^])(?:\{([^{}]*)\}|([A-Za-z0-9+-]))', script, value)
    # Remaining braces denote grouping; preserve that grouping explicitly.
    value = value.replace('{','(').replace('}',')')
    return value


def math_markdown(text):
    # Fenced/inline code is opaque, including code that happens to contain $...$.
    pattern = re.compile(r'(?ms)^([ \t]*)(`{3,}|~{3,})[^\n]*\n.*?(?:^\1\2[^\n]*(?:\n|$)|\Z)|`+[^`\n]*`+|'
                         r'(?<!\\)\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)|(?<![\\$])\$([^$\n]+)\$(?!\$)')
    def replace(m):
        formula = next((part for part in m.groups()[2:] if part is not None), None)
        if formula is None:
            return m[0]
        # Do not mistake a pair of currency prices for an inline formula.
        if m[6] is not None and not re.search(r'[\\_^=+*/<>]|\b[A-Za-z]\b|^\s*[\d.]+\s*$',formula):
            return m[0]
        converted = readable_math(formula)
        if m[3] is not None or m[4] is not None:
            return '\n\n```math\n'+converted+'\n```\n\n'
        fence = '`' * max(1, max((len(x) for x in re.findall(r'`+',converted)), default=0)+1)
        return fence + converted + fence
    return pattern.sub(replace,text)


def has_formatting(text):
    return bool(re.search(r'(?m)^\s*(?:#{1,6}\s|```|~~~|[-*+]\s|\d+[.)]\s|>\s|\|.*\||:?-{3,}:?\s*\|)|'
                          r'\*\*|__|`|\$|\\[([]|(?<!\w)\*[^*\n]+\*(?!\w)',text))


class LocalDocument(QTextDocument):
    def loadResource(self, kind, name):
        # Model Markdown must never read a file or fetch a remote resource.
        return QByteArray()


def formatted_fragment(text, font):
    document = LocalDocument()
    document.setDefaultFont(font)
    document.setMarkdown(math_markdown(text), QTextDocument.MarkdownDialectGitHub | QTextDocument.MarkdownNoHTML)
    cursor = QTextCursor(document)
    cursor.select(QTextCursor.Document)
    cursor.mergeCharFormat(reply_text_format())
    # Remove image objects entirely before insertion into the real browser;
    # disable anchors so model text cannot navigate that browser away from chat.
    edits = []
    block = document.begin()
    while block.isValid():
        fragment = block.begin()
        while not fragment.atEnd():
            part = fragment.fragment()
            cf = part.charFormat()
            if cf.isImageFormat() or cf.isAnchor():
                edits.append((part.position(),part.length(),cf.isImageFormat()))
            fragment += 1
        block = block.next()
    for position,length,image in reversed(edits):
        cursor.setPosition(position);cursor.setPosition(position+length,QTextCursor.KeepAnchor)
        if image:
            cursor.insertText('[Image]')
        else:
            cf=cursor.charFormat();cf.setAnchor(False);cf.setAnchorHref('');cursor.setCharFormat(cf)
    families = set(QFontDatabase.families())
    fixed = next((name for name in ('Menlo','DejaVu Sans Mono','Liberation Mono','Consolas','Courier New')
                  if name in families), QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
    block = document.begin()
    while block.isValid():
        cursor = QTextCursor(block)
        bf = block.blockFormat()
        bf.setBottomMargin(10)
        if bf.headingLevel():
            bf.setTopMargin(12);bf.setBottomMargin(12)
        if bf.hasProperty(QTextFormat.BlockCodeFence):
            bf.setBackground(QColor('#102943'));bf.setLeftMargin(12);bf.setRightMargin(12)
            previous=block.previous().blockFormat();following=block.next().blockFormat()
            bf.setTopMargin(8 if previous.property(QTextFormat.BlockCodeLanguage) != bf.property(QTextFormat.BlockCodeLanguage) else 0)
            bf.setBottomMargin(8 if following.property(QTextFormat.BlockCodeLanguage) != bf.property(QTextFormat.BlockCodeLanguage) else 0)
            # Wrapping is visual only: copying retains code whitespace/newlines.
            bf.setNonBreakableLines(False);cursor.setBlockFormat(bf)
            cursor.select(QTextCursor.BlockUnderCursor)
            cf=cursor.charFormat();cf.setFontFamilies([fixed]);cursor.mergeCharFormat(cf)
        else:
            cursor.setBlockFormat(bf)
        block=block.next()
    def tables(frame):
        for child in frame.childFrames():
            if isinstance(child,QTextTable):
                tf=child.format();tf.setBorder(1);tf.setBorderBrush(QColor('#52708e'))
                tf.setCellPadding(8);tf.setCellSpacing(0);tf.setBackground(QColor('#10243c'))
                tf.setWidth(QTextLength(QTextLength.PercentageLength,100))
                tf.setColumnWidthConstraints([QTextLength(QTextLength.PercentageLength,100/child.columns())]*child.columns())
                child.setFormat(tf)
                for row in range(child.rows()):
                    for column in range(child.columns()):
                        cell=child.cellAt(row,column);cf=cell.format()
                        cf.setBackground(QColor('#1d3855' if row == 0 else '#10243c'));cell.setFormat(cf)
            tables(child)
    tables(document.rootFrame())
    return QTextDocumentFragment(document)


def trim_transcript(view, limit=500):
    document=view.document()
    # Qt's automatic block limit is undefined for documents containing tables.
    # Trim old top-level text/frames at reply boundaries instead.
    document.setMaximumBlockCount(0)
    if document.blockCount() <= limit:
        return
    block=document.findBlockByNumber(document.blockCount()-limit)
    cursor=QTextCursor(block)
    frame=cursor.currentFrame()
    if frame != document.rootFrame():
        while frame.parentFrame() != document.rootFrame():
            frame=frame.parentFrame()
        end=min(document.characterCount()-1,frame.lastPosition()+1)
    else:
        end=block.position()
    cursor=QTextCursor(document);cursor.setPosition(end,QTextCursor.KeepAnchor);cursor.removeSelectedText()
