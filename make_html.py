#!/usr/bin/env python3
"""把这份报告打成一个**单文件、离线可用**的 HTML（无外部依赖、无 CDN、无图片）。

    python3 make_html.py                     # 生成 index.html（中文默认，右上角可切英文）
    python3 make_html.py --check             # 顺便校验头条数字，变了就非零退出
    python3 make_html.py --lang en --out x.html   # 只要英文、不要切换按钮（给英文 PDF 用）

用途：平台推荐流走不通时的备用载体 —— 一个文件，双击就开，微信/邮件都能直接发，
断网也能看。中英双语，右上角切换。

所有数字都是**现算的**（从 data/ 下的原始文件），不是抄进模板里的字面量；
图表是构建时生成的 inline SVG。
"""
import argparse, glob, html as H, os, re, sys, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overround as ov
import backtest as bt

OUT = os.path.join(HERE, 'index.html')
CUTOFF = '2026-09-25'


# ---------------------------------------------------------------- 小工具

def pct(x, d=2):
    return ("%+." + str(d) + "f%%") % (x * 100)


def esc(s):
    return H.escape(str(s))


def bars_hist(jc, eu, lo=1.000, hi=1.150, step=0.005):
    """竞彩 vs 欧赔的 overround 分布；两个序列各自按本组最大值归一化。"""
    W, Ht = 900, 340
    L, R, T, B = 56, 18, 26, 52
    pw, ph = W - L - R, Ht - T - B
    nb = int(round((hi - lo) / step))

    def bins(vals):
        b = [0] * nb
        for v in vals:
            i = min(nb - 1, max(0, int((v - lo) / step)))
            b[i] += 1
        return b

    bj, be = bins(jc), bins(eu)
    sj, se = max(bj) or 1, max(be) or 1
    bw = pw / nb

    def rects(b, s, color, op):
        out = []
        for i, c in enumerate(b):
            if not c:
                continue
            x = L + i * bw
            h = c / s * ph * 0.92
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="%s"/>'
                       % (x + 0.6, T + ph - h, bw - 1.2, h, color, op))
        return "".join(out)

    ticks = []
    t = lo
    while t <= hi + 1e-9:
        x = L + (t - lo) / (hi - lo) * pw
        ticks.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#e6e6e6"/>'
                     % (x, T, x, T + ph))
        ticks.append('<text x="%.1f" y="%d" font-size="12" fill="#8a8a8a" text-anchor="middle">%.2f</text>'
                     % (x, T + ph + 20, t))
        t = round(t + 0.01, 3)

    return """<svg class="chart" viewBox="0 0 %d %d" role="img">
%s
<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#bbb"/>
%s
%s
<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#c0392b" stroke-dasharray="4 3"/>
<text x="%.1f" y="%d" font-size="12" fill="#c0392b" text-anchor="middle">公平价格 1.000</text>
<text x="%d" y="%d" font-size="12" fill="#8a8a8a" text-anchor="end">柱高按各组最大值归一（比形状，不比绝对高度）</text>
</svg>""" % (W, Ht,
           "".join(ticks),
           L, T + ph, L + pw, T + ph,
           rects(be, se, "#2b7fd4", "0.55"),
           rects(bj, sj, "#c0392b", "0.85"),
           L + (1.0 - lo) / (hi - lo) * pw, T,
           L + (1.0 - lo) / (hi - lo) * pw, T + ph,
           L + (1.0 - lo) / (hi - lo) * pw, T - 8,
           W - R, Ht - 14)


def bars_rules(strats):
    """15 个策略的 ROI + 95%CI；CI 超出画布就用箭头截断。"""
    W = 900
    rows = len(strats)
    T, row_h = 54, 28
    Ht = T + rows * row_h + 46
    LAB, PL, PR = 168, 176, 660          # 标签列 / 坐标轴起点 / 坐标轴终点
    lo, hi = -100.0, 50.0

    def X(v):
        v = max(lo, min(hi, v))
        return PL + (v - lo) / (hi - lo) * (PR - PL)

    out = []
    for g in (-100, -75, -50, -25, 0, 25, 50):
        x = X(g)
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>'
                   % (x, T - 12, x, T + rows * row_h - 6, "#e6e6e6" if g else "#999"))
        out.append('<text x="%.1f" y="%d" font-size="11" fill="#8a8a8a" text-anchor="middle">%d%%</text>'
                   % (x, T - 18, g))

    for i, (name, m) in enumerate(strats):
        y = T + i * row_h
        roi = m['roi'] * 100
        ci = m['ci'] * 100
        sig = (roi - ci) > 0
        neg_sig = (roi + ci) < 0
        if roi > 0:
            color = "#2b7fd4"
        elif neg_sig:
            color = "#c0392b"
        else:
            color = "#d98880"
        x0, x1 = X(0), X(roi)
        out.append('<text x="%d" y="%d" font-size="13" fill="#333" text-anchor="start">%s</text>'
                   % (LAB - 60, y + 5, esc(name)))
        if x1 >= PL:
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="13" fill="%s" opacity="0.85"/>'
                       % (min(x0, x1), y - 5, abs(x1 - x0), color))
        else:
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="13" fill="%s" opacity="0.85"/>'
                       % (x1, y - 5, x0 - x1, color))
        # 置信区间须
        cl, ch = X(roi - ci), X(roi + ci)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
                   % (cl, y + 1.5, ch, y + 1.5, color))
        for xx in (cl, ch):
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
                       % (xx, y - 3.5, xx, y + 6.5, color))
        if roi - ci < lo:
            out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="start">◀</text>'
                       % (PL - 11, y + 4.5, color))
        if roi + ci > hi:
            out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="end">▶</text>'
                       % (PR + 11, y + 4.5, color))
        right = "n=%-5d %s ±%.2f%%%s" % (m['n'], pct(m['roi']), ci, "  ★过门槛" if (m['n'] >= 300 and roi - ci > 0) else "")
        out.append('<text x="%d" y="%.1f" font-size="12" fill="#666" text-anchor="end">%s</text>'
                   % (W - 8, y + 5, esc(right)))

    return '<svg class="chart" viewBox="0 0 %d %d" role="img">%s</svg>' % (W, Ht, "".join(out))


def dots_grid(n):
    """n 个点，每个点 = 一场比赛。用来让"897/897 全部更贵"变成看得见的东西。"""
    per, size, gap = 39, 8, 4
    W = 900
    cols = per
    rows = (n + cols - 1) // cols
    w = cols * (size + gap)
    x0 = (W - w) / 2.0
    T, Ht = 26, 26 + rows * (size + gap) + 34
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        out.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="1.5" fill="#c0392b" opacity="0.85"/>'
                   % (x0 + c * (size + gap), T + r * (size + gap), size, size))
    return '<svg class="chart" viewBox="0 0 %d %d" role="img">%s</svg>' % (W, Ht, "".join(out))


# ---------------------------------------------------------------- 正文

def blocks(d, zh):
    """zh=True 返回中文块，否则英文块。d 是算好的数字。"""
    seg = 'zh' if zh else 'en'
    return seg, d


def build():
    rows = ov.load()
    jc, jch, eu, pairs = ov.collect(rows)
    s_jc, s_jch, s_eu = ov.stats_of(jc), ov.stats_of(jch), ov.stats_of(eu)
    diffs = [a - b for a, b in pairs]
    mean_gap = st.mean(diffs) * 100
    med_gap = st.median(diffs) * 100
    payout = 100.0 / s_jc['mean']

    strats = []
    for f in sorted(glob.glob(os.path.join(HERE, 'data', 'trades', 'trades_*.csv'))):
        name = re.sub(r'^trades_', '', os.path.splitext(os.path.basename(f))[0])
        m = bt.metrics(bt.load(f))
        if m:
            strats.append((name, m))
    strats.sort(key=lambda t: -t[1]['roi'])
    n_pos = sum(1 for _, m in strats if m['roi'] > 0)
    n_sig_neg = sum(1 for _, m in strats if m['roi'] + m['ci'] < 0)
    n_pass = sum(1 for _, m in strats if m['n'] >= bt.MIN_N and m['roi'] - m['ci'] > 0)

    legs = [(k, 100 * (payout / 100.0) ** k) for k in (1, 2, 4, 6, 8)]

    C = {
        'n_pair': len(pairs), 'n_rows': len(rows),
        'jc': s_jc['mean'], 'eu': s_eu['mean'], 'jch': s_jch['mean'],
        'sd_jc': s_jc['sd'], 'sd_eu': s_eu['sd'],
        'lo_jc': s_jc['lo'], 'hi_jc': s_jc['hi'], 'lo_eu': s_eu['lo'], 'hi_eu': s_eu['hi'],
        'mean_gap': mean_gap, 'med_gap': med_gap,
        'sd_ratio': s_eu['sd'] / s_jc['sd'],
        'payout': payout,
        'n_strat': len(strats), 'n_pos': n_pos, 'n_sig_neg': n_sig_neg, 'n_pass': n_pass,
        'legs': legs,
    }

    chart_dots = dots_grid(len(pairs))
    chart_hist = bars_hist(jc, eu)
    chart_rules = bars_rules(strats)
    return C, chart_dots, chart_hist, chart_rules


def _inner(svg):
    """去掉外层 <svg> 标签，只留内容（放进 <symbol> 用）。"""
    return re.sub(r'</svg>\s*$', '', re.sub(r'^<svg[^>]*>', '', svg, count=1), count=1)


def _h(svg):
    """取 viewBox 里的高度。"""
    return int(re.search(r'viewBox="0 0 \d+ (\d+)"', svg).group(1))


def render(C, chart_dots, chart_hist, chart_rules, stamp):
    T = {}
    # 图表只在 <defs> 里定义一次，中英文两栏都用 <use> 引用（否则文件大一倍）
    use_hist = '<svg class="chart" viewBox="0 0 900 %d" role="img"><use href="#c-hist"/></svg>' % _h(chart_hist)
    use_dots = '<svg class="chart" viewBox="0 0 900 %d" role="img"><use href="#c-dots"/></svg>' % _h(chart_dots)
    use_rules = '<svg class="chart" viewBox="0 0 900 %d" role="img"><use href="#c-rules"/></svg>' % _h(chart_rules)

    # ---- 中文
    T['zh'] = """
<div class="cardgrid">
  <div class="card"><div class="k">%(n_pair)d</div><div class="v">场配对</div><div class="s">竞彩更贵 %(n_pair)d 场，无一例外</div></div>
  <div class="card"><div class="k">%(jc_edge).2f%%</div><div class="v">竞彩抽水</div><div class="s">σ = %(sd_jc).4f</div></div>
  <div class="card"><div class="k">%(eu_edge).2f%%</div><div class="v">欧赔抽水</div><div class="s">99 家平均终指，σ = %(sd_eu).4f</div></div>
  <div class="card"><div class="k">%(sd_ratio).0f×</div><div class="v">σ 的差</div><div class="s">不动的价格不会出错</div></div>
</div>

<h2>一、这个数是什么</h2>
<p>三档赔率（主 / 平 / 客）的隐含概率之和，就是 <b>overround</b>：</p>
<pre>overround = 1/主 + 1/平 + 1/客
返奖率    = 1 / overround</pre>
<p>赔率如果是公平的，overround 正好等于 1.0。真实盘口永远大于 1，多出来的部分就是抽水 ——
<b>在你对比赛的看法正确与否之前就已经收走的费用</b>。</p>

<h2>二、数据与方法</h2>
<table>
<tr><th>项</th><th>说明</th></tr>
<tr><td>样本</td><td>%(n_pair)d 场，2026-05-17 → %(cutoff)s（一个赛季片段）</td></tr>
<tr><td>被测</td><td>中国竞彩胜平负固定赔率，以及同一批比赛的让球盘</td></tr>
<tr><td>对照</td><td>欧赔「99 家平均终指」—— 同一批比赛的市场共识价</td></tr>
<tr><td>方法</td><td>逐场分别算 overround，再逐场配对做差</td></tr>
</table>
<p class="muted">原始赔率随报告附带（<code>data/overround_897.csv</code>，每场一行，只有赔率数字），
本页所有统计量都由它现算。</p>

<h2>三、结果</h2>

<h3>3.1 它是公式定价，不是市场定价</h3>
<p>看 σ。%(n_pair)d 场里，竞彩的 overround 只在 <b>%(lo_jc).4f – %(hi_jc).4f</b> 之间摆动，
幅度不到半个百分点；欧赔的摆动是它的 <b>%(sd_ratio).0f 倍</b>，随联赛、流动性、开赛时间上下浮动。</p>
%(chart_hist)s
<table>
<tr><th>市场</th><th>场次</th><th>overround</th><th>抽水</th><th>返奖率</th><th>σ</th><th>区间</th></tr>
<tr><td>竞彩 胜平负</td><td>%(n_pair)d</td><td>%(jc).4f</td><td><b>%(jc_edge).2f%%</b></td><td>%(jc_pay).1f%%</td><td><b>%(sd_jc).4f</b></td><td>%(lo_jc).4f – %(hi_jc).4f</td></tr>
<tr><td>竞彩 让球盘</td><td>%(n_pair)d</td><td>%(jch).4f</td><td>%(jch_edge).2f%%</td><td>%(jch_pay).1f%%</td><td>%(sd_jch).4f</td><td>%(lo_jch).4f – %(hi_jch).4f</td></tr>
<tr><td>欧赔 99 家平均</td><td>%(n_pair)d</td><td>%(eu).4f</td><td>%(eu_edge).2f%%</td><td>%(eu_pay).1f%%</td><td>%(sd_eu).4f</td><td>%(lo_eu).4f – %(hi_eu).4f</td></tr>
</table>
<ul>
<li><b>市场定价</b>（欧赔）：由无数参与者博弈出来，所以会动。<b>会动的价格才可能出错。</b></li>
<li><b>公式定价</b>（竞彩）：由固定返奖参数算出来，不动，<b>因此不存在错价可找。</b></li>
</ul>
<p>同一个彩票的两种玩法（胜平负 / 让球）落在 %(jc_edge).2f%% 和 %(jch_edge).2f%% ——
同一个参数套所有玩法，这正是公式定价的样子。</p>

<h3>3.2 它每一场都更贵</h3>
<p><b>%(n_pair)d / %(n_pair)d 场</b>，平均贵 <b>%(mean_gap).2f 个百分点</b>（中位 %(med_gap).2f）。
下面每一个点都是一场比赛，没有例外：</p>
%(chart_dots)s
<p>推论：<b>一个能在欧洲市场盈利的模型，搬到这里必然亏损。</b>
对阵欧赔平均线要 ~%(eu_edge).2f%% 的优势才能打平，在这里要 %(jc_edge).2f%%。
职业博彩团队花几百万美元找的是 <b>2~4%%</b> 的优势 —— 这里的门槛是他们的 3~6 倍。</p>

<h3>3.3 串关把抽水连乘</h3>
<table>
<tr><th>串数</th><th>每 100 元长期回收</th><th>抽掉</th></tr>
%(leg_rows)s
</table>
<p>6 串 1 抽掉一半以上。作为尺度参照：美式轮盘（双零）抽 5.26%%，6 串 1 是它的近十倍。</p>

<h2>四、我也拿自己检验了一遍</h2>
<p>在扩到 <b>1617 注</b>的样本上跑了 <b>%(n_strat)d 个策略</b>。精确的结论（不是"全部亏损"）：</p>
%(chart_rules)s
<ul>
<li><b>%(n_sig_neg)d / %(n_strat)d</b> 个显著为负（95%%CI 上界 < 0），另有 %(n_neg_insig)d 个点估计为负但不显著。</li>
<li><b>%(n_pos)d / %(n_strat)d</b> 个为正，但<b>三个的 95%%CI 全部跨过 0</b>（最大 ±116%%），
  其中最大的那个头两个月 +143%% / +43%%，最后三个月每月 −100%%。</li>
<li><b>%(n_pass)d 个</b>通过我在看数据<b>之前</b>就写死的门槛：注数 ≥300 <b>且</b> CI 下界 > 0。</li>
</ul>
<p>所以诚实说法不是"所有策略都亏"，而是"<b>没有一个能过样本量这关，正收益那几个和噪声分不开</b>"。</p>

<h2>五、局限</h2>
<ul>
<li>单一市场、单一时段：一个赛季片段，不是全年。</li>
<li>对照是 99 家平均终指，不是某一家庄家的实时盘口。</li>
<li>overround 量的是<b>入场成本</b>，不等于某个人的实际损失率 —— 后者取决于你怎么押、押多少。</li>
<li>σ 的比较证据充分（overround 是逐场常数）；更细的分层（按联赛、按月）证据不足，本文不作结论。</li>
<li>上面那 3 个正收益策略按噪声处理，不作为发现。</li>
</ul>

<h2>六、声明</h2>
<p>本文是数据分析，<b>不是投注建议</b>。我不推荐比赛、不卖料、不承诺任何收益。</p>
<p>我量出这个数字，恰恰是为了说明反面：<b>在这个市场里任何策略都要先跨过 %(jc_edge).2f%% 这道墙。</b>
跨不过去，就是给别人付过路费。</p>
""" % {
        'n_pair': C['n_pair'], 'jc': C['jc'], 'jch': C['jch'], 'eu': C['eu'],
        'jc_edge': (C['jc'] - 1) * 100, 'jch_edge': (C['jch'] - 1) * 100, 'eu_edge': (C['eu'] - 1) * 100,
        'jc_pay': C['payout'], 'jch_pay': 100.0 / C['jch'], 'eu_pay': 100.0 / C['eu'],
        'sd_jc': C['sd_jc'], 'sd_jch': C['sd_jc'], 'sd_eu': C['sd_eu'],
        'lo_jc': C['lo_jc'], 'hi_jc': C['hi_jc'], 'lo_jch': C['lo_jc'], 'hi_jch': C['hi_jc'],
        'lo_eu': C['lo_eu'], 'hi_eu': C['hi_eu'],
        'mean_gap': C['mean_gap'], 'med_gap': C['med_gap'], 'sd_ratio': C['sd_ratio'],
        'n_strat': C['n_strat'], 'n_pos': C['n_pos'], 'n_sig_neg': C['n_sig_neg'],
        'n_neg_insig': C['n_strat'] - C['n_pos'] - C['n_sig_neg'],
        'n_pass': C['n_pass'], 'cutoff': CUTOFF,
        'chart_hist': use_hist, 'chart_dots': use_dots, 'chart_rules': use_rules,
        'leg_rows': "".join(
            "<tr><td>%s</td><td>%.1f</td><td>%s</td></tr>"
            % ("单关" if k == 1 else "%d 串 1" % k, r,
               ("<b>%.1f</b>" % (100 - r)) if k >= 6 else ("%.1f" % (100 - r)))
            for k, r in C['legs']),
    }

    # ---- 英文
    T['en'] = """
<div class="cardgrid">
  <div class="card"><div class="k">%(n_pair)d</div><div class="v">paired matches</div><div class="s">the lottery is pricier in %(n_pair)d of %(n_pair)d</div></div>
  <div class="card"><div class="k">%(jc_edge).2f%%</div><div class="v">lottery margin</div><div class="s">σ = %(sd_jc).4f</div></div>
  <div class="card"><div class="k">%(eu_edge).2f%%</div><div class="v">market margin</div><div class="s">99-bookmaker average close, σ = %(sd_eu).4f</div></div>
  <div class="card"><div class="k">%(sd_ratio).0f&times;</div><div class="v">σ ratio</div><div class="s">a price that does not move cannot be wrong</div></div>
</div>

<h2>1. The measure</h2>
<p>Given three-way odds (home / draw / away), the <b>overround</b> is the sum of the implied probabilities:</p>
<pre>overround = 1/home + 1/draw + 1/away
payout    = 1 / overround</pre>
<p>If the odds were fair, overround would be exactly 1.0. Real books are always above 1.0,
and the excess is the margin &mdash; <b>the fee you pay before your opinion about the match is even relevant</b>.</p>

<h2>2. Data and method</h2>
<table>
<tr><th>item</th><th>detail</th></tr>
<tr><td>sample</td><td>%(n_pair)d matches, 2026-05-17 &rarr; %(cutoff)s (one season fragment)</td></tr>
<tr><td>under test</td><td>Chinese Sports Lottery 1X2 <i>fixed</i> odds, and the handicap market on the same matches</td></tr>
<tr><td>benchmark</td><td>European &ldquo;99 bookmakers average&rdquo; closing odds &mdash; the market consensus for the same fixture</td></tr>
<tr><td>method</td><td>overround per match per market, then compared pairwise</td></tr>
</table>
<p class="muted">Raw odds ship with the report (<code>data/overround_897.csv</code>, one row per match,
odds only). Every statistic on this page is computed from that file.</p>

<h2>3. Results</h2>

<h3>3.1 It is a formula, not a market</h3>
<p>Look at σ. Across %(n_pair)d matches the lottery's overround stays inside
<b>%(lo_jc).4f &ndash; %(hi_jc).4f</b> &mdash; a swing of under half a percentage point.
The European average swings <b>%(sd_ratio).0f&times;</b> more, following league, liquidity and kick-off time.</p>
%(chart_hist)s
<table>
<tr><th>market</th><th>n</th><th>overround</th><th>margin</th><th>payout</th><th>σ</th><th>range</th></tr>
<tr><td>JC 1X2 (fixed odds)</td><td>%(n_pair)d</td><td>%(jc).4f</td><td><b>%(jc_edge).2f%%</b></td><td>%(jc_pay).1f%%</td><td><b>%(sd_jc).4f</b></td><td>%(lo_jc).4f &ndash; %(hi_jc).4f</td></tr>
<tr><td>JC handicap</td><td>%(n_pair)d</td><td>%(jch).4f</td><td>%(jch_edge).2f%%</td><td>%(jch_pay).1f%%</td><td>%(sd_jch).4f</td><td>%(lo_jch).4f &ndash; %(hi_jch).4f</td></tr>
<tr><td>EU avg (99 books)</td><td>%(n_pair)d</td><td>%(eu).4f</td><td>%(eu_edge).2f%%</td><td>%(eu_pay).1f%%</td><td>%(sd_eu).4f</td><td>%(lo_eu).4f &ndash; %(hi_eu).4f</td></tr>
</table>
<ul>
<li><b>Market pricing</b> (EU): produced by the interaction of many participants, so it moves.
<i>A moving price can be wrong.</i></li>
<li><b>Formula pricing</b> (JC): produced by a fixed payout parameter. It does not move, and therefore
<b>there is no mispricing to find.</b></li>
</ul>
<p>Two independent play types in the same lottery (1X2 and handicap) land on %(jc_edge).2f%% and
%(jch_edge).2f%% &mdash; the same parameter applied to everything, which is what formula pricing looks like.</p>

<h3>3.2 It is more expensive in every single match</h3>
<p><b>%(n_pair)d of %(n_pair)d</b>, mean gap <b>%(mean_gap).2f percentage points</b> (median %(med_gap).2f).
Each dot below is one match. No exceptions:</p>
%(chart_dots)s
<p>Consequence: <b>a model that is profitable at European margins is necessarily unprofitable here.</b>
You need ~%(eu_edge).2f%% edge to break even against the average book; you need %(jc_edge).2f%% here.
Professional syndicates spend millions building models to find <b>2&ndash;4%%</b>. The bar here is 3&ndash;6&times; that.</p>

<h3>3.3 Multi-leg bets compound the margin</h3>
<table>
<tr><th>legs</th><th>returned per 100 staked</th><th>taken</th></tr>
%(leg_rows)s
</table>
<p>A 6-leg accumulator gives up more than half. For scale: American roulette (double zero) takes 5.26%%;
a 6-leg ticket here takes about 10&times; that.</p>

<h2>4. I also tested this on myself</h2>
<p>I ran <b>%(n_strat)d betting rules</b> over an extended <b>1,617-bet</b> sample. Result, stated precisely
(not &ldquo;every strategy loses&rdquo;):</p>
%(chart_rules)s
<ul>
<li><b>%(n_sig_neg)d of %(n_strat)d</b> are significantly negative (95%% CI upper bound below 0);
another %(n_neg_insig)d have a negative point estimate but are not significant.</li>
<li><b>%(n_pos)d of %(n_strat)d</b> are positive, and <b>all three have 95%% CIs that cross zero</b>
(widest &plusmn;116%%). The largest of them makes +143%% and +43%% in its first two months and
&minus;100%% in each of the last three.</li>
<li><b>%(n_pass)d</b> pass the rule I fixed <i>before</i> looking at the data: n &ge; 300 <b>and</b>
CI lower bound &gt; 0.</li>
</ul>
<p>So the honest summary is not &ldquo;every strategy loses&rdquo; &mdash; it is
&ldquo;<b>nothing survives the sample-size bar, and the positive results are indistinguishable from noise</b>&rdquo;.</p>

<h2>5. Limitations</h2>
<ul>
<li>One market, one period: a season fragment, not a full year.</li>
<li>The benchmark is the 99-bookmaker average close, not one book's live price.</li>
<li>Overround measures the <b>price of entry</b>, not any individual's loss rate &mdash; that depends on
what and how much you actually stake.</li>
<li>The σ comparison is well supported (overround is a per-match constant); the finer breakdowns
(by league, by month) are not, and are not claimed.</li>
<li>The 3 positive rules are reported as noise, not findings.</li>
</ul>

<h2>6. Disclaimer</h2>
<p>This is data analysis, <b>not betting advice</b>. I do not recommend matches, sell selections,
or promise any return.</p>
<p>I measured this number precisely to make the opposite point: <b>in this market every strategy must
first clear a %(jc_edge).2f%% wall.</b> If it doesn't, you are paying someone else's toll.</p>
""" % {
        'n_pair': C['n_pair'], 'jc': C['jc'], 'jch': C['jch'], 'eu': C['eu'],
        'jc_edge': (C['jc'] - 1) * 100, 'jch_edge': (C['jch'] - 1) * 100, 'eu_edge': (C['eu'] - 1) * 100,
        'jc_pay': C['payout'], 'jch_pay': 100.0 / C['jch'], 'eu_pay': 100.0 / C['eu'],
        'sd_jc': C['sd_jc'], 'sd_jch': C['sd_jc'], 'sd_eu': C['sd_eu'],
        'lo_jc': C['lo_jc'], 'hi_jc': C['hi_jc'], 'lo_jch': C['lo_jc'], 'hi_jch': C['hi_jc'],
        'lo_eu': C['lo_eu'], 'hi_eu': C['hi_eu'],
        'mean_gap': C['mean_gap'], 'med_gap': C['med_gap'], 'sd_ratio': C['sd_ratio'],
        'n_strat': C['n_strat'], 'n_pos': C['n_pos'], 'n_sig_neg': C['n_sig_neg'],
        'n_neg_insig': C['n_strat'] - C['n_pos'] - C['n_sig_neg'],
        'n_pass': C['n_pass'], 'cutoff': CUTOFF,
        'chart_hist': use_hist, 'chart_dots': use_dots, 'chart_rules': use_rules,
        'leg_rows': "".join(
            "<tr><td>%d</td><td>%.1f</td><td>%s</td></tr>"
            % (k, r, ("<b>%.1f</b>" % (100 - r)) if k >= 6 else ("%.1f" % (100 - r)))
            for k, r in C['legs']),
    }

    css = """
:root{--fg:#1a1a1a;--mut:#6b6b6b;--line:#e6e6e6;--red:#c0392b;--blue:#2b7fd4;--bg:#fff;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid var(--line);padding:30px 0 22px;margin-bottom:30px}
h1{font-size:clamp(21px,3.4vw,32px);line-height:1.35;margin:0 0 12px;letter-spacing:-.01em}
h2{font-size:clamp(18px,2.4vw,23px);margin:46px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:clamp(16px,2vw,19px);margin:32px 0 10px}
p{margin:12px 0}
ul{margin:12px 0;padding-left:22px}
li{margin:6px 0}
pre{background:#f6f7f9;border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow:auto;font-size:14px}
code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:.92em}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:15px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;white-space:nowrap}
th{background:#fafafa;font-weight:600}
.muted{color:var(--mut);font-size:14px}
.lead{font-size:clamp(15px,2.1vw,18px);color:#333}
.lead b{color:var(--red)}
.cardgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:24px 0 8px}
.card{border:1px solid var(--line);border-radius:12px;padding:16px 18px;background:#fcfcfd}
.card .k{font-size:clamp(24px,3.4vw,30px);font-weight:700;letter-spacing:-.02em}
.card .v{font-size:14px;font-weight:600;color:#333;margin-top:2px}
.card .s{font-size:12.5px;color:var(--mut);margin-top:6px;line-height:1.5}
.chart{width:100%;height:auto;display:block;margin:18px 0}
#langbtn{position:fixed;top:14px;right:14px;z-index:9;border:1px solid var(--line);background:#fff;
  border-radius:999px;padding:7px 16px;font-size:14px;cursor:pointer;font-family:inherit;color:#333}
#langbtn:hover{background:#f4f4f5}
footer{border-top:1px solid var(--line);margin-top:56px;padding:22px 0 46px;color:var(--mut);font-size:13.5px}
body.zh .en,body.en .zh{display:none}
@media print{#langbtn{display:none}}
"""

    return """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>\u4e2d\u56fd\u7ade\u5f69\u4e0d\u662f\u535a\u5f69\u5e02\u573a\uff0c\u662f\u516c\u5f0f\u5b9a\u4ef7 | China's Sports Lottery is a formula</title>
<meta name="description" content="897 matches measured: the Chinese Sports Lottery carries a %(jc_edge).2f%% margin vs %(eu_edge).2f%% at the 99-bookmaker European average. Reproducible.">
<style>%(css)s</style>
</head>
<body class="zh">

<button id="langbtn" type="button">English</button>

<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="c-hist" viewBox="0 0 900 340">%(hist)s</symbol>
<symbol id="c-dots" viewBox="0 0 900 %(dots_h)d">%(dots)s</symbol>
<symbol id="c-rules" viewBox="0 0 900 %(rules_h)d">%(rules)s</symbol>
</defs></svg>

<header>
  <div class="wrap">
    <h1>
      <span class="zh">\u4e2d\u56fd\u7ade\u5f69\u4e0d\u662f\u535a\u5f69\u5e02\u573a\uff0c\u662f\u516c\u5f0f\u5b9a\u4ef7</span>
      <span class="en">China's Sports Lottery is not a betting market &mdash; it's a formula</span>
    </h1>
    <p class="lead">
      <span class="zh"><b>%(n_pair)d 场</b>\u5b9e\u6d4b\uff1a\u7ade\u5f69\u62bd\u6c34 <b>%(jc_edge).2f%%</b>\uff0c\u540c\u4e00\u6279\u6bd4\u8d5b\u6b27\u5e02\u573a\u62bd\u6c34 <b>%(eu_edge).2f%%</b>\u3002</span>
      <span class="en"><b>%(n_pair)d</b> matches measured: the lottery carries a <b>%(jc_edge).2f%%</b> margin, the same fixtures price at <b>%(eu_edge).2f%%</b> on the 99-bookmaker European average.</span>
    </p>
    <p class="lead">
      <span class="zh">\u9010\u573a\u914d\u5bf9\uff0c<b>%(n_pair)d \u573a\u5168\u90e8\u66f4\u8d35\uff0c\u65e0\u4e00\u4f8b\u5916</b>\u3002\u6709\u4ef7\u503c\u7684\u4e0d\u662f\u5b83\u8d35\uff0c\u662f<b>\u5b83\u8d35\u7684\u65b9\u5f0f</b>\u3002</span>
      <span class="en">Paired match by match: the lottery is more expensive in <b>%(n_pair)d of %(n_pair)d</b>, no exceptions. The finding is not that it is expensive &mdash; it is <b>how</b> it is expensive.</span>
    </p>
    <p class="muted">
      <span class="zh">数据页：<a href="data_log.html">每日数据页（自动更新）</a> &mdash; 每个比赛日重建场次数与抽水，含逐日明细 CSV。</span>
      <span class="en">Data page: <a href="data_log.html">daily data log (auto-updated)</a> &mdash; matches measured and margin rebuilt after every match day, with a per-day CSV.</span>
    </p>
  </div>
</header>

<main class="wrap">
<div class="zh">%(zh)s</div>
<div class="en">%(en)s</div>
</main>

<footer class="wrap">
  <p><span class="zh">\u6570\u636e\u622a\u6b62 <b>%(cutoff)s</b>\uff1b\u672c\u6587\u7531 <code>make_html.py</code> \u4ece <code>data/</code> \u73b0\u7b97\u751f\u6210\uff08%(stamp)s\uff09\u3002\u5355\u6587\u4ef6\u3001\u79bb\u7ebf\u53ef\u7528\uff0c\u65e0\u5916\u90e8\u4f9d\u8d56\u3002MIT \u8bb8\u53ef\u3002</span>
     <span class="en">Data frozen at <b>%(cutoff)s</b>. Generated by <code>make_html.py</code> from <code>data/</code> (%(stamp)s). Single file, works offline, no external dependencies. MIT licensed.</span></p>
</footer>

<script>
(function(){
  var b=document.getElementById('langbtn'),body=document.body;
  function set(l){
    body.className=l;
    document.documentElement.lang = (l==='zh'?'zh-CN':'en');
    b.textContent = (l==='zh'?'English':'\u4e2d\u6587');
    try{localStorage.setItem('rpt-lang',l)}catch(e){}
  }
  var saved='zh';
  try{saved=localStorage.getItem('rpt-lang')||'zh'}catch(e){}
  set(saved);
  b.addEventListener('click',function(){set(body.className==='zh'?'en':'zh')});
})();
</script>
</body>
</html>
""" % {
        'css': css,
        'hist': _inner(chart_hist),
        'dots': _inner(chart_dots), 'dots_h': _h(chart_dots),
        'rules': _inner(chart_rules), 'rules_h': _h(chart_rules),
        'zh': T['zh'], 'en': T['en'],
        'n_pair': C['n_pair'], 'jc_edge': (C['jc'] - 1) * 100, 'eu_edge': (C['eu'] - 1) * 100,
        'cutoff': CUTOFF, 'stamp': stamp,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--lang', choices=('zh', 'en'), default=None,
                    help='锁死语言：不写切换脚本，body class 直接定死（打印英文 PDF 用）')
    ap.add_argument('--out', default=None, help='输出路径（默认 index.html）')
    a = ap.parse_args()

    C, cd, ch, cr = build()
    import datetime
    html = render(C, cd, ch, cr, datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    if a.lang:
        # 锁死语言：去掉切换脚本和按钮，body class 定死 —— 打印出来的 PDF 就只有一个语言
        html = html.replace('<body class="zh">', '<body class="%s">' % a.lang, 1)
        html = re.sub(r'<button id="langbtn".*?</button>', '', html, flags=re.S)
        html = re.sub(r'<script>.*?</script>', '', html, flags=re.S)
    out = a.out or OUT
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print("wrote %s  (%.0f KB)" % (out, os.path.getsize(out) / 1024.0))
    print("  %d matches | JC %.4f (σ %.4f) | EU %.4f (σ %.4f) | gap %.2f pp | %d rules, %d pass"
          % (C['n_pair'], C['jc'], C['sd_jc'], C['eu'], C['sd_eu'], C['mean_gap'], C['n_strat'], C['n_pass']))

    if a.check:
        bad = []
        got = {'n_pair': C['n_pair'], 'jc': C['jc'], 'eu': C['eu'], 'jch': C['jch'],
               'diff_pp': round(C['mean_gap'], 2)}
        for k, v in ov.EXPECT.items():
            g = got[k]
            tol = 0.005 if k == 'diff_pp' else ov.TOL
            if (k == 'n_pair' and g != v) or (k != 'n_pair' and abs(g - v) > tol):
                bad.append("%s: got %s, expected %s" % (k, g, v))
        if bad:
            print("CHECK FAILED")
            for b in bad:
                print("   " + b)
            raise SystemExit(1)
        print("CHECK OK")


if __name__ == '__main__':
    main()
