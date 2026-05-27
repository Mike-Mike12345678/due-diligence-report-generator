# 客户尽调报告生成器（Due Diligence Report Generator）

> 输入一个公司名，自动生成 4-6 页专业排版的客户尽调初稿 PDF。

## 它能做什么？

给定任意一家公司名（如"比亚迪"、"Tesla"），工具会自动：

1. **搜集信息** - 多轮网络搜索，覆盖公司基本面、战略动向、AI 应用三个维度
2. **深度分析** - 交叉验证、提炼洞察、识别信息缺口、生成合作切入点
3. **生成报告** - 按专业模板生成 PDF，包含封面、目录、4 大章节、免责声明

最终输出一份包含以下内容的尽调初稿：

| 章节 | 内容 |
|------|------|
| 01 公司业务概览 | 成立时间、主营业务、营收规模、行业地位、核心产品、财务概况 |
| 02 近三年关键战略动向 | 重大投资/并购、组织调整、技术路线、市场扩张、趋势研判 |
| 03 AI 应用现状分析 | AI 产品/项目、技术团队、专利布局、投入方向、行业对比 |
| 04 与软通计算的合作切入点 | 3 个具体合作建议，含推荐理由、合作方式和优先级 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入你的 API Key：

```yaml
llm:
  base_url: "https://your-api-endpoint/v1"
  api_key: "你的API-Key"
  model: "模型名"
  model_advanced: "高级模型名"

search:
  api_key: "你的Tavily-API-Key"
```

**需要两个 API Key**：
- **LLM API Key**：任何 OpenAI 兼容接口均可（智谱 GLM / DeepSeek / OpenAI 等）
- **Tavily API Key**：从 https://tavily.com 获取（有免费额度）

### 3. 运行

```bash
python main.py -c "比亚迪"
```

报告会生成在 `output/` 目录下，包含：
- `XX_尽调报告_YYYY-MM-DD.pdf` - 最终 PDF 报告
- `XX_research.json` - 信息搜集中间结果
- `XX_analysis.json` - 深度分析中间结果

## 使用示例

```bash
# 基本用法
python main.py -c "比亚迪"

# 海外公司（自动使用英文搜索）
python main.py -c "Tesla"

# 指定输出目录
python main.py -c "华为" -o ./reports/

# 显示详细日志
python main.py -c "中国移动" -v
```

## 命令行参数

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `--company` | `-c` | 目标公司名称（必填） | - |
| `--config` | | 配置文件路径 | `config.yaml` |
| `--output` | `-o` | 输出目录 | `./output` |
| `--verbose` | `-v` | 显示详细日志 | `false` |

## 工作原理

### 三步流水线架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Research Agent  │───>│  Analysis Agent  │───>│   Report Agent   │
│   信息搜集       │    │   深度分析       │    │   报告生成       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Step 1: Research Agent（信息搜集）**
- 分 3 轮搜索：公司基本面 → 战略动向 → AI 应用
- 每轮 3 个搜索关键词，自动识别中/英文（无中文字符则视为海外公司）
- LLM 从搜索结果中提取结构化数据
- 自动按 URL 去重，合并多轮结果

**Step 2: Analysis Agent（深度分析）**
- 5 步分析：业务概览 → 战略分析 → AI 分析 → 合作切入点 → 信息缺口检查
- 结合内置的软通计算能力模型（`knowledge/softcom_profile.md`）生成合作建议
- 智能识别信息缺口并触发补充搜索，搜索结果回灌到分析数据中
- 所有分析步骤使用高级模型以确保质量

**Step 3: Report Agent（报告生成）**
- 将分析结果映射为报告章节结构
- LLM 对短章节自动扩展、对正常章节润色增强
- 生成专业排版的 PDF（ReportLab 引擎）

### 比直接问大模型好在哪？

这是本工具的核心价值。直接在豆包/DeepSeek 等模型的聊天端输入"帮我做一份 XX 公司的尽调报告"，你会得到泛泛而谈的答案。本工具在每一步都加了价值：

| 对比维度 | 直接问模型 | 本工具 |
|----------|-----------|--------|
| **信息来源** | 仅训练知识，可能过时数月甚至数年 | **实时网络搜索 + 多源验证**，获取最新公开信息 |
| **搜索广度** | 单次对话，信息有限 | **3 轮 × 3 个关键词 = 9 次定向搜索**，覆盖基本面/战略/AI 三个维度 |
| **信息提取** | 依赖模型记忆，可能"幻觉" | **从真实搜索结果中结构化提取**，减少编造风险 |
| **分析深度** | 一遍生成，浅尝辄止 | **5 步渐进式分析**：概览→战略→AI→合作→缺口检查 |
| **软通视角** | 无行业洞察，泛泛建议 | **内置软通计算能力模型**，合作建议与软通实际能力精准匹配 |
| **信息补充** | 不补不查 | **自动识别缺口 → 触发补充搜索 → 提取新信息 → 回灌分析** |
| **可复现性** | 每次不同，无法追溯 | **固定工作流 + 中间 JSON 保存**，可复用/再加工 |
| **排版质量** | 纯文本输出 | **专业 PDF 排版**（封面/目录/页码/表格/章节结构） |

**一句话总结**：本工具 = 实时搜索 + 结构化提取 + 多步深度分析 + 领域知识注入 + 自动排版，而直接问模型只是"一次对话生成"。

## 项目结构

```
due-diligence-skill/
├── main.py                # CLI 入口
├── pipeline.py            # 流水线编排
├── config.yaml.example    # 配置模板
├── requirements.txt       # Python 依赖
├── README.md              # 本文档
├── agents/
│   ├── research.py        # 信息搜集 Agent
│   ├── analysis.py        # 深度分析 Agent
│   └── report.py          # 报告生成 Agent
├── utils/
│   ├── llm_client.py      # LLM API 封装（OpenAI 兼容）
│   ├── search_client.py   # Tavily 搜索封装
│   ├── pdf_engine.py      # PDF 生成引擎（ReportLab）
│   └── schemas.py         # 数据契约定义
├── prompts/
│   ├── research.md        # Research Agent prompt 模板
│   ├── analysis.md        # Analysis Agent prompt 模板
│   └── report.md          # Report Agent prompt 模板
├── knowledge/
│   └── softcom_profile.md # 软通计算能力模型
└── output/                # 报告输出目录
```

## 配置说明

```yaml
llm:
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  api_key: "your-api-key"
  model: "glm-4-flash"               # 搜集用模型（速度快）
  model_advanced: "glm-4-plus"       # 分析/报告用模型（质量高）
  temperature: 0.3

search:
  api_key: "your-tavily-key"
  max_results: 5                      # 每次搜索返回结果数（建议 3-10）
  search_depth: "basic"               # basic（快）或 advanced（详）
  include_raw_content: false
  timeout: 30

report:
  language: "zh"
  output_dir: "./output"

pipeline:
  max_research_rounds: 3              # 信息搜集轮数
  retry_on_failure: 2                 # 失败重试次数
  verbose: false
```

**支持的 LLM**：任何兼容 OpenAI 接口的 API 均可使用，包括但不限于：
- 智谱 GLM（glm-4-flash、glm-4-plus、glm-5-turbo）
- DeepSeek（deepseek-chat、deepseek-v4-flash）
- OpenAI（gpt-4o、gpt-4o-mini）
- 其他兼容 OpenAI 格式的第三方 API

## 自定义

- **修改合作建议视角**：编辑 `knowledge/softcom_profile.md`，调整软通能力模型
- **调整分析行为**：编辑 `prompts/` 目录下的 prompt 模板
- **调整 PDF 样式**：编辑 `utils/pdf_engine.py` 中的样式定义

## FAQ

**Q: 需要哪些 API Key？**
A: 两个：LLM API Key（任何 OpenAI 兼容接口）和 Tavily API Key（https://tavily.com，有免费额度）。

**Q: 支持哪些 LLM？**
A: 任何兼容 OpenAI Chat API 格式的服务都可以。只需配置 `base_url`、`api_key` 和 `model` 即可。

**Q: 支持海外公司吗？**
A: 支持。工具会自动检测公司名是否包含中文字符，不含则自动切换为英文关键词搜索。

**Q: 一份报告大概要多久？**
A: 通常 3-8 分钟。取决于 API 响应速度和搜索结果数量。大部分时间花在 LLM 调用上（约 10 次对话）。

**Q: 报告内容准确吗？**
A: 报告基于实时公开信息生成，会进行交叉验证。但仍建议作为"初稿"使用，关键信息需要人工核实。

**Q: 中间结果在哪？**
A: 每一步的中间结果会保存为 JSON 文件在 `output/` 目录下（`_research.json` 和 `_analysis.json`），可用于调试、复用或二次加工。

## 技术栈

- **Python 3.10+**
- **LLM**: 任何 OpenAI 兼容 API（智谱 GLM / DeepSeek / OpenAI 等）
- **搜索**: Tavily Search API
- **PDF**: ReportLab（内置 CID 中文字体，纯 Python 无系统依赖）
- **CLI**: Click
- **日志**: Rich
