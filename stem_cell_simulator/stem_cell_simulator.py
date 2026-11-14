"""Stem Cell Self-Renewal & Differentiation Simulator (single file, Tkinter, no installs).
Run:  python stem_cell_simulator.py
"""
import math, random, time
import tkinter as tk


# ======== PART A - visuals: colour helpers and all cell drawing on a Tk canvas. ========

BG, R = '#0a0e2e', 62
TYPES = {
    'neuron': dict(name='Neuron (Nerve Cell)', color='#a78bfa', signal='NGF + retinoic acid', gene='NEUROD1',
                   fn='Dendrites receive messages; the axon carries electrical impulses to other cells.'),
    'muscle': dict(name='Muscle Cell', color='#fb7185', signal='FGF / IGF-1', gene='MYOD1',
                   fn='Long fibres with striations (sarcomeres) contract to produce movement.'),
    'blood':  dict(name='Blood Cell (Red Blood Cell)', color='#f87171', signal='erythropoietin (EPO)', gene='GATA1',
                   fn='Biconcave discs packed with haemoglobin carry oxygen around the body.'),
}

def _rgb(c): return [int(c[i:i + 2], 16) for i in (1, 3, 5)]
def blend(a, b, t):
    x, y = _rgb(a), _rgb(b)
    return '#%02x%02x%02x' % tuple(int(x[i] + (y[i] - x[i]) * t) for i in range(3))
def mix(c, a): return blend(BG, c, max(0, min(1, a)))      # fake transparency against the background
def lerp(a, b, t): return a + (b - a) * t
def oval(cv, x, y, rx, ry, fill, outline='', w=1): cv.create_oval(x - rx, y - ry, x + rx, y + ry, fill=fill, outline=outline, width=w)
def glow(cv, x, y, rx, ry, color, a=1):
    for i in range(8, 0, -1):
        k = 1 + i * .08; oval(cv, x, y, rx * k, ry * k, mix(color, a * .045 * (9 - i)))

def recpos(i):  # receptor i on the membrane, relative to the cell centre
    ang = i * math.pi / 4 + .2; return math.cos(ang) * R, math.sin(ang) * R

def draw_stem(cv, c, t):
    a = c.alpha
    if a <= .02: return
    k = 1 + .025 * math.sin(t * 2.2); sx, s = c.sx, c.s; rx, ry = R * s * sx * k, R * s * k; x, y = c.x, c.y
    glow(cv, x, y, rx, ry, '#22d3ee', a)
    for i in range(9):  # layered ovals = radial gradient
        oval(cv, x - rx * .03 * i, y - ry * .035 * i, rx * (1 - i * .09), ry * (1 - i * .09),
             mix(blend('#6366f1', '#a5f3fc', i / 8), a), mix('#67e8f9', a) if i == 0 else '', 3)
    for mx, my in [(-34, -28), (32, -34), (-38, 26), (34, 30)]:  # mitochondria
        oval(cv, x + mx * s * sx, y + my * s, 9 * s * sx, 5 * s, mix('#f0abfc', a * .8))
    nr = 26 * s * (1 + (.1 * math.sin(t * 8) if c.nuc_on else 0))  # nucleus (pulses when gene is switched on)
    if c.nuc_on: glow(cv, x, y, nr * sx, nr, '#c4b5fd', a)
    oval(cv, x, y, nr * sx, nr, mix('#7c3aed', a), mix('#ddd6fe', a), 2)
    oval(cv, x - 6 * s * sx, y - 7 * s, 8 * s * sx, 7 * s, mix('#c4b5fd', a * .8))
    for i in range(8):  # receptors
        ang = i * math.pi / 4 + .2; dx, dy = math.cos(ang), math.sin(ang)
        bx, by = x + dx * R * s * sx * k, y + dy * R * s * k; tx, ty = bx + dx * 10 * s, by + dy * 10 * s
        col = mix('#ffffff' if i in c.rec_on else '#fde68a', a)
        cv.create_line(bx, by, tx, ty, fill=col, width=2)
        for sg in (-1, 1):
            cv.create_line(tx, ty, tx + math.cos(ang + sg * .6) * 9 * s, ty + math.sin(ang + sg * .6) * 9 * s, fill=col, width=2)

def _bez(p0, p1, p2, p3, n=24):
    return [tuple((1 - u) ** 3 * p0[j] + 3 * (1 - u) ** 2 * u * p1[j] + 3 * (1 - u) * u * u * p2[j] + u ** 3 * p3[j] for j in (0, 1))
            for u in (i / n for i in range(n + 1))]
_DEN = [((-30, -12), (-70, -40), (-90, -60), (-110, -92)), ((-34, 0), (-80, 0), (-100, 10), (-130, 16)), ((-28, 14), (-60, 40), (-80, 70), (-100, 96)),
        ((-8, -34), (-10, -60), (0, -80), (15, -102)), ((10, -32), (30, -60), (50, -72), (70, -92)), ((-8, 34), (-5, 60), (-20, 80), (-30, 102))]
_LINES = [(_bez(*d), 5) for d in _DEN] + [(_bez((34, 0), (120, 0), (160, -10), (250, 0)) + [(290, 0)], 8)] + \
         [([(290, 0), e], 4) for e in ((332, -32), (338, 0), (332, 32))]

def draw_neuron(cv, cx, cy, p, a):
    ox = cx - 130; col = '#a78bfa'; f = max(0, min(1, (p - .2) / .8))
    for pts, w in _LINES:
        n = int(len(pts) * f)
        if n < 2: continue
        flat = [v for q in pts[:n] for v in (ox + q[0], cy + q[1])]
        cv.create_line(*flat, width=w + 7, fill=mix(col, a * .25), capstyle='round', joinstyle='round')
        cv.create_line(*flat, width=w, fill=mix(col, a), capstyle='round', joinstyle='round')
    r = R - 26 * p; glow(cv, ox, cy, r, r, col, a)
    oval(cv, ox, cy, r, r, mix('#7c3aed', a), mix('#ddd6fe', a), 3); oval(cv, ox, cy, 15, 15, mix('#c4b5fd', a), mix('#4c1d95', a), 2)

def draw_muscle(cv, cx, cy, p, a):
    W, H = lerp(2 * R, 340, p), lerp(2 * R, 80, p); r = H / 2
    for col, w in ((mix('#fb7185', a * .25), 10), (mix('#fda4af', a), 3)):  # soft halo, then bright edge
        cv.create_rectangle(cx - W / 2 + r, cy - r, cx + W / 2 - r, cy + r, fill=mix('#be123c', a), outline='', width=0)
        oval(cv, cx - W / 2 + r, cy, r, r, mix('#be123c', a), col, w); oval(cv, cx + W / 2 - r, cy, r, r, mix('#be123c', a), col, w)
    cv.create_rectangle(cx - W / 2 + r, cy - r, cx + W / 2 - r, cy + r, fill=mix('#be123c', a), outline='')
    for i in range(14):  # striations fade in
        x = cx + (-150 + i * 23) * W / 340; cv.create_line(x, cy - H * .42, x, cy + H * .42, fill=mix('#fecdd3', a * p * .45), width=3)
    for x in (-110, -30, 60, 130): oval(cv, cx + x * W / 340, cy - H * .35, 12, 6, mix('#4c1d95', a))

def draw_blood(cv, cx, cy, p, a):
    for x, y in ((-190, -80), (-200, 70), (195, 60), (170, -105)):
        b = a * max(0, min(1, (p - .5) * 2)); oval(cv, cx + x, cy + y, 30, 30, mix('#b91c1c', b), mix('#fca5a5', b), 2); oval(cv, cx + x, cy + y, 14, 10, mix('#450a0a', b * .7))
    glow(cv, cx, cy, R, R, '#ef4444', a)
    for i in range(7): oval(cv, cx - i * 1.2, cy - i * 1.4, R - i * 8, R - i * 8, mix(blend('#ef4444', '#7f1d1d', i / 6), a), mix('#fca5a5', a) if i == 0 else '', 3)
    oval(cv, cx, cy, 32, 24, mix('#450a0a', a * p * .6))

def draw_special(cv, sp, cx, cy):
    {'neuron': draw_neuron, 'muscle': draw_muscle, 'blood': draw_blood}[sp['kind']](cv, cx, cy, sp['p'], sp['a'])


# ======== PART A - visuals: Tkinter dashboard (header, canvas, controls, explanation panel, info cards). ========
BG, PANEL, EDGE, CY, TX, MU = '#0a0e2e', '#131a4a', '#2e3a8c', '#67e8f9', '#e2e8f0', '#94a3b8'
CARDS = [('signal', 'Biological signal', 'A chemical message (growth factor, hormone) from nearby cells telling a stem cell what to do.'),
         ('receptor', 'Cell receptor', 'A membrane protein that binds one specific signal molecule and relays the message inside.'),
         ('gene', 'Gene expression', 'Switching genes on/off so the cell makes certain proteins: lineage genes on, stem-cell genes off.'),
         ('renewal', 'Self-renewal', 'Division giving daughter cells that are still stem cells, so the pool is never used up.'),
         ('diff', 'Differentiation', 'A stem cell commits to a lineage and gains the shape and proteins of a specialised cell.')]

class UI:
    def __init__(self, root, cb):
        self.kind, self.lbl = tk.StringVar(value='neuron'), ('', '')
        root.title('Stem Cell Self-Renewal & Differentiation Simulator'); root.configure(bg=BG, padx=16, pady=12)
        head = tk.Frame(root, bg=BG); head.pack(fill='x')
        tk.Label(head, text='Stem Cell Self-Renewal & Differentiation Simulator', font=('Segoe UI', 17, 'bold'), fg='#fff', bg=BG).pack(side='left')
        self.stats = {}
        for k, name in (('stage', 'stage'), ('spec', 'specialised'), ('stem', 'stem cells')):
            f = tk.Frame(head, bg=PANEL, highlightbackground=EDGE, highlightthickness=1, padx=12, pady=3); f.pack(side='right', padx=4)
            self.stats[k] = tk.Label(f, text='-', font=('Segoe UI', 13, 'bold'), fg=CY, bg=PANEL); self.stats[k].pack()
            tk.Label(f, text=name, font=('Segoe UI', 8), fg=MU, bg=PANEL).pack()
        body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, pady=10)
        self.cv = tk.Canvas(body, width=800, height=500, bg=BG, highlightthickness=1, highlightbackground=EDGE); self.cv.pack(side='left')
        side = tk.Frame(body, bg=BG); side.pack(side='left', fill='both', expand=True, padx=(12, 0))
        box = self._panel(side, 'Controls'); self.locked = []
        for text, key, primary, lock in (('Start Simulation', 'sim', 1, 1), ('Start Self-Renewal', 'ren', 0, 1), ('Start Differentiation', 'diff', 0, 1), ('Pause', 'pause', 0, 0), ('Reset', 'reset', 0, 0)):
            b = tk.Button(box, text=text, command=cb[key], bg='#6d28d9' if primary else '#1e2766', fg='#fff', activebackground='#0891b2', activeforeground='#fff',
                          relief='flat', bd=0, pady=7, font=('Segoe UI', 10, 'bold' if primary else 'normal'), disabledforeground='#5b6499', cursor='hand2')
            b.pack(fill='x', pady=2)
            if lock: self.locked.append(b)
            if key == 'pause': self.pause_btn = b
        tk.Label(box, text='Differentiate into', fg=MU, bg=PANEL, font=('Segoe UI', 9)).pack(anchor='w', pady=(8, 2))
        row = tk.Frame(box, bg=PANEL); row.pack(fill='x')
        for text, v in (('Neuron', 'neuron'), ('Muscle cell', 'muscle'), ('Blood cell', 'blood')):
            tk.Radiobutton(row, text=text, value=v, variable=self.kind, indicatoron=0, bg='#1e2766', fg=TX, selectcolor='#5b3fc4', activebackground='#2a3590',
                           relief='flat', bd=0, pady=6, cursor='hand2').pack(side='left', expand=True, fill='x', padx=2)
        ex = self._panel(side, "What's happening"); self.ex = {}
        for k, h in (('what', 'What is happening?'), ('why', 'Why is it happening?'), ('concept', 'Concept demonstrated')):
            tk.Label(ex, text=h, fg=CY, bg=PANEL, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
            self.ex[k] = tk.Label(ex, text='', fg=TX, bg=PANEL, wraplength=290, justify='left', font=('Segoe UI', 10)); self.ex[k].pack(anchor='w', pady=(0, 6))
        row = tk.Frame(root, bg=BG); row.pack(fill='x'); self.cards = {}
        for i, (k, title, text) in enumerate(CARDS):
            row.columnconfigure(i, weight=1, uniform='c')
            f = tk.Frame(row, bg=PANEL, highlightbackground=EDGE, highlightthickness=2, padx=8, pady=6); f.grid(row=0, column=i, sticky='nsew', padx=4)
            tk.Label(f, text=title, fg='#fff', bg=PANEL, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
            tk.Label(f, text=text, fg=MU, bg=PANEL, wraplength=170, justify='left', font=('Segoe UI', 8)).pack(anchor='w'); self.cards[k] = f

    def _panel(self, parent, title):
        f = tk.Frame(parent, bg=PANEL, highlightbackground=EDGE, highlightthickness=1, padx=12, pady=10); f.pack(fill='x', pady=(0, 10))
        tk.Label(f, text=title, fg=MU, bg=PANEL, font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4)); return f

    # --- the only methods the logic code calls ---
    def explain(self, what, why, concept, key):
        for k, v in (('what', what), ('why', why), ('concept', concept)): self.ex[k].config(text=v)
        for k, f in self.cards.items(): f.config(highlightbackground=CY if k == key else EDGE)
    def count(self, stem, spec): self.stats['stem'].config(text=stem); self.stats['spec'].config(text=spec)
    def stage(self, t): self.stats['stage'].config(text=t)
    def label(self, title, sub): self.lbl = (title, sub)
    def lock(self, b):
        for x in self.locked: x.config(state='disabled' if b else 'normal')
    def draw_label(self):
        self.cv.create_text(400, 468, text=self.lbl[0], fill='#fff', font=('Segoe UI', 14, 'bold'))
        self.cv.create_text(400, 490, text=self.lbl[1], fill=MU, font=('Segoe UI', 10))


# ======== PART B - logic: pausable animation engine. Simulation steps are generators that `yield tween(...)`. ========

def ease(p): return 2 * p * p if p < .5 else 1 - (-2 * p + 2) ** 2 / 2
def lerp(a, b, t): return a + (b - a) * t
def tween(seconds, fn): return (seconds, fn)          # fn(progress 0..1) is called every frame
def wait(seconds): return (seconds, lambda p: None)

class Engine:
    def __init__(self, root, on_frame):
        self.root, self.on_frame, self.job, self.cur, self.el, self.paused, self.done = root, on_frame, None, None, 0, False, None
        self.last = time.perf_counter(); self._loop()
    def busy(self): return self.job is not None
    def start(self, gen, on_done=None): self.job, self.done, self.cur = gen, on_done, None; self._next()
    def cancel(self): self.job = self.cur = None; self.paused = False
    def _next(self):
        try: self.cur, self.el = next(self.job), 0
        except StopIteration:
            self.job = self.cur = None
            if self.done: self.done()
    def _loop(self):
        now = time.perf_counter(); dt = min(.05, now - self.last); self.last = now
        if self.job and not self.paused and self.cur:
            self.el += dt; secs, fn = self.cur; p = min(1, self.el / secs); fn(ease(p))
            if p >= 1: self._next()
        self.on_frame(dt)
        self.root.after(16, self._loop)


# ======== PART B - logic: everything that exists on the stage, and how to draw it. ========

class Cell:
    def __init__(self, x, y, s): self.x, self.y, self.s, self.sx, self.alpha, self.rec_on, self.nuc_on = x, y, s, 1, 1, set(), False

class Scene:
    def __init__(self):
        random.seed(3); self.bokeh = [(random.randint(0, 800), random.randint(0, 500), random.randint(3, 14)) for _ in range(28)]; self.reset()
    def reset(self): self.cells, self.mols, self.ring, self.tag, self.special, self.t = [Cell(400, 250, 1)], [], None, None, None, 0
    def draw(self, cv):
        cv.delete('all')
        for x, y, r in self.bokeh: oval(cv, x, y, r, r, mix('#6366f1', .07))
        for c in self.cells: draw_stem(cv, c, self.t)
        for m in self.mols: glow(cv, m['x'], m['y'], 7, 7, m['color']); oval(cv, m['x'], m['y'], 7, 7, mix(m['color'], 1))
        if self.ring: x, y, r, col, a = self.ring; oval(cv, x, y, r, r, '', mix(col, a), 3)
        if self.tag: txt, a = self.tag; cv.create_text(400, 140, text=txt, fill=mix('#ffffff', a), font=('Segoe UI', 16, 'bold'))
        if self.special: draw_special(cv, self.special, 400, 250)


# ======== PART B - logic: self-renewal. Cells elongate, then split into two identical stem cells. ========
MAX = 8

def layout(n):  # centred grid; cells shrink as the population grows
    s = 1 if n <= 1 else .75 if n <= 2 else .6 if n <= 4 else .45; cols = n if n <= 2 else 4; rows = -(-n // cols); gap = 135 * s; out = []
    for i in range(n):
        r, k = i // cols, min(cols, n - i // cols * cols)
        out.append((400 + (i % cols - (k - 1) / 2) * gap, 250 + (r - (rows - 1) / 2) * gap, s))
    return out

def set_label(app):
    n = len(app.scene.cells); app.ui.label(f'{n} Undifferentiated Stem Cells' if n > 1 else 'Undifferentiated Stem Cell', 'Can self-renew or differentiate')

def divide(app):
    s, ui = app.scene, app.ui
    if not s.cells: ui.explain('No stem cell left on the stage.', 'The cell already differentiated; press Reset to start again.', 'Differentiation', 'diff'); return
    if len(s.cells) >= MAX: ui.explain(f'Display limit of {MAX} cells reached.', 'Real populations keep doubling; the cap only keeps cells visible.', 'Self-renewal', 'renewal'); return
    ui.stage('Self-renewal')
    ui.explain('The cell grows, copies its DNA and starts dividing (mitosis).', 'To make more stem cells so the stem-cell pool is never used up.', 'Self-renewal', 'renewal')
    old = list(s.cells); L = layout(len(old) * 2); st = [(c.x, c.y, c.s) for c in old]
    def elongate(p):
        for c in old: c.sx = 1 + .45 * p
    yield tween(1.0, elongate)
    kids = []
    for c in old: k = Cell(c.x, c.y, c.s); k.sx = 1.45; kids.append(k)
    s.cells = old + kids
    def split(p):
        for i, c in enumerate(old):
            for o, t in ((c, L[2 * i]), (kids[i], L[2 * i + 1])):
                o.x, o.y, o.s, o.sx = lerp(st[i][0], t[0], p), lerp(st[i][1], t[1], p), lerp(st[i][2], t[2], p), lerp(1.45, 1, p)
    yield tween(1.2, split)
    s.cells = [c for pair in zip(old, kids) for c in pair]
    ui.count(len(s.cells), 0); ui.stage('Ready'); set_label(app)
    ui.explain(f'Two identical daughter cells. Stem cells now: {len(s.cells)}.', 'Both daughters keep stem-cell genes (e.g. OCT4, SOX2), so the population is maintained and can grow.', 'Self-renewal', 'renewal')


# ======== PART B - logic: differentiation. Signal -> receptor -> gene expression -> new shape. ========

def run_differentiation(app, kind):
    s, ui, T = app.scene, app.ui, TYPES[kind]
    if not s.cells: ui.explain('No stem cell on the stage.', 'Press Reset to get a fresh stem cell.', 'Differentiation', 'diff'); return
    c, others = s.cells[0], s.cells[1:]; st = (c.x, c.y, c.s)
    # 1. isolate one cell and centre it
    ui.stage('Differentiation'); ui.label('Undifferentiated Stem Cell', 'Waiting for a signal')
    ui.explain('One stem cell is selected and centred.', 'Differentiation is decided cell by cell, by the signals each one receives.', 'Differentiation', 'diff')
    def centre(p):
        for o in others: o.alpha = 1 - p
        c.x, c.y, c.s = lerp(st[0], 400, p), lerp(st[1], 250, p), lerp(st[2], 1, p)
    yield tween(.8, centre); s.cells = [c]
    # 2. signal molecules travel to receptors on the left side of the membrane
    ui.explain(f'Signal molecules ({T["signal"]}) reach the cell.', 'Cells respond to chemical signals from their surroundings.', 'Biological signal', 'signal')
    idx = [3, 4, 5]; s.mols = []
    for i in range(6):
        rx, ry = recpos(idx[i % 3]); s.mols.append(dict(x=0, y=0, color=T['color'], x0=50 + random.random() * 90, y0=60 + i * 70, tx=400 + rx, ty=250 + ry))
    def fly(p):
        for i, m in enumerate(s.mols):
            q = max(0, min(1, (p - i * .08) / .6)); m['x'], m['y'] = lerp(m['x0'], m['tx'], q), lerp(m['y0'], m['ty'], q)
    yield tween(2.2, fly)
    # 3. receptor binding
    c.rec_on = set(idx)
    ui.explain('Signal molecules bind to receptor proteins on the membrane.', 'Each receptor fits one molecule like a lock and key, passing the message inside.', 'Cell receptors', 'receptor')
    yield wait(1.4)
    # 4. gene expression in the nucleus
    c.nuc_on = True
    ui.explain(f'The message reaches the nucleus and the gene {T["gene"]} is switched on.', 'Gene expression decides which proteins the cell makes, and so what it becomes.', 'Gene expression', 'gene')
    def express(p): s.ring = (400, 250, 30 + 60 * p, T['color'], 1 - p); s.tag = (f'{T["gene"]} switched ON', min(1, p * 2))
    yield tween(1.8, express)
    # 5. morph into the specialised cell
    ui.explain(f'The cell reshapes into a {T["name"]}.', 'New proteins rebuild its structure while stem-cell genes are switched off.', 'Differentiation', 'diff')
    s.special = dict(kind=kind, p=0, a=0)
    def morph(p): c.alpha = 1 - p; s.special.update(p=p, a=min(1, p * 1.5)); s.tag = (s.tag[0], 1 - p)
    yield tween(2.6, morph)
    s.cells, s.mols, s.ring, s.tag = [], [], None, None
    # 6. result
    ui.count(0, 1); ui.stage('Differentiated'); ui.label(T['name'], T['fn'])
    ui.explain(f'A mature {T["name"]} has formed.', T['fn'], 'Differentiation', 'diff')


# ======== PART B - logic: run this file.  python main.py ========

class App:
    def __init__(self):
        self.root = tk.Tk(); self.scene = Scene()
        self.ui = UI(self.root, dict(sim=self.sim, ren=lambda: self.job(divide(self)), diff=lambda: self.job(run_differentiation(self, self.ui.kind.get())),
                                     pause=self.pause, reset=self.reset))
        self.engine = Engine(self.root, self.frame); self.reset()
    def frame(self, dt):
        if not self.engine.paused: self.scene.t += dt
        self.scene.draw(self.ui.cv); self.ui.draw_label()
    def job(self, gen):
        if self.engine.busy(): return
        self.ui.lock(True); self.engine.start(gen, lambda: self.ui.lock(False))
    def sim(self):  # guided demo: divide twice, then differentiate
        self.reset()
        def demo():
            yield from divide(self); yield wait(.5); yield from divide(self); yield wait(.6)
            yield from run_differentiation(self, self.ui.kind.get())
        self.job(demo())
    def pause(self):
        self.engine.paused = not self.engine.paused; self.ui.pause_btn.config(text='Resume' if self.engine.paused else 'Pause')
    def reset(self):
        self.engine.cancel(); self.scene.reset(); self.ui.lock(False); self.ui.pause_btn.config(text='Pause')
        self.ui.count(1, 0); self.ui.stage('Idle'); set_label(self)
        self.ui.explain('A single undifferentiated stem cell.', 'It has not committed to a lineage, so it can still divide or become many cell types.', 'Stem-cell potency', 'renewal')



if __name__ == '__main__':
    App().root.mainloop()
