import os, json, subprocess, tempfile, shlex
from typing import List, Optional
from pathlib import Path

# Optional OpenAI SDK import (only used when OPENAI_API_KEY is set)
try:
    import openai  # type: ignore
except Exception:
    openai = None
from utils.llm_cost import LLMCostTracker

class GPTClient:
    def __init__(self, model: str = "gpt-4o-mini", demo_mode: bool = False):
        self.model = model
        # Allow env override to force demo mode
        env_demo = os.getenv("GPT_DEMO_MODE")
        self.demo_mode = True if env_demo == "1" else demo_mode
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_cost = LLMCostTracker()
        self.last_cost: Optional[dict] = None
        # External CLI hook
        self.cli_cmd = os.getenv("LLM_CLI_CMD")  # e.g., "llm -m gemini-pro --file {file}" or "claude --file --format json"
        # Gemini API direct
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Force latest default: Gemini 2.5 Pro (can be overridden by env)
        self.gemini_model = "gemini-2.5-pro"
        os.environ["GEMINI_MODEL"] = self.gemini_model
        # Preferred provider: default to env or gemini (GUI may override)
        self.preferred_provider = os.getenv("LLM_PROVIDER", "gemini")
        
        # Claude Code利用可能性をチェック
        self.claude_code_available = self._check_claude_code()
        
        # Claude Code案内の表示は、プロバイダがauto/claude_cliのときのみ
        # （geminiやopenaiを明示選択している場合はノイズを出さない）
        if self.claude_code_available and not self.demo_mode:
            preferred = os.getenv("LLM_PROVIDER", "auto")
            if preferred in ("auto", "claude_cli"):
                print("🤖 Claude Code呼び出しモード: 直接Claude Codeを使用します")
        elif not self.api_key or self.api_key in ["", "ere", "your-api-key-here"]:
            self.demo_mode = True
            print("🧪 GPT Demo Mode: スタブデータを使用します")

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract a JSON object substring from arbitrary text.
        Returns the JSON text between the first '{' and the last '}', if valid.
        """
        try:
            if not text:
                return None
            s = text.strip()
            # Strip common Markdown fences
            if s.startswith('```json') and s.endswith('```'):
                s = s[7:-3].strip()
            elif s.startswith('```') and s.endswith('```'):
                s = s[3:-3].strip()
            i, j = s.find('{'), s.rfind('}')
            if i >= 0 and j > i:
                return s[i:j+1]
            return None
        except Exception:
            return None
    
    def _check_claude_code(self) -> bool:
        """Claude Codeが利用可能かチェック"""
        try:
            # claude commandの存在確認
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
            
            # 一般的なパスをチェック
            possible_paths = [
                '/usr/local/bin/claude',
                '/opt/homebrew/bin/claude',
                Path.home() / '.local' / 'bin' / 'claude'
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    return True
                
            return False
        except Exception:
            return False
    
    def _call_claude_code(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Claude Codeを直接呼び出し"""
        try:
            # 一時ファイルにプロンプトを保存
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                if system_prompt:
                    f.write(f"System: {system_prompt}\n\nUser: {prompt}")
                else:
                    f.write(prompt)
                temp_file = f.name
            
            # Claude Codeを呼び出し
            cmd = ['claude', '--file', temp_file, '--format', 'text']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # 一時ファイル削除
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Claude Code error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Claude Code呼び出しエラー: {e}")
            return None

    def _call_cli_json(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Call external LLM CLI defined by LLM_CLI_CMD and return stdout text."""
        if not self.cli_cmd:
            return None
        try:
            # Write prompt to a temp file (include system prompt header if provided)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                if system_prompt:
                    f.write(f"System: {system_prompt}\n\nUser: {prompt}")
                else:
                    f.write(prompt)
                temp_file = f.name
            cmd = self.cli_cmd
            if '{file}' in cmd:
                cmd = cmd.replace('{file}', shlex.quote(temp_file))
            else:
                cmd = cmd + ' ' + shlex.quote(temp_file)
            # Execute via shell to allow pipelines/options
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            # Cleanup
            try:
                os.unlink(temp_file)
            except Exception:
                pass
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"LLM_CLI_CMD failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"CLI hook error: {e}")
            return None

    def _generate_with_gemini(self, prompt: str) -> Optional[str]:
        """Direct Gemini API call, returns response text if possible (JSON expected)."""
        try:
            import requests
            if not self.gemini_api_key:
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
            r = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
            if r.status_code != 200:
                print(f"Gemini API error: {r.status_code} {r.text[:200]}")
                return None
            jr = r.json()
            # Extract text
            candidates = jr.get("candidates", [])
            if candidates and candidates[0].get("content", {}).get("parts"):
                parts = candidates[0]["content"]["parts"]
                text = ''.join(p.get("text", "") for p in parts)
                
                # Handle markdown-wrapped JSON (```json...```)
                text = text.strip()
                if text.startswith('```json') and text.endswith('```'):
                    # Remove markdown wrapper
                    text = text[7:-3].strip()
                elif text.startswith('```') and text.endswith('```'):
                    # Remove generic markdown wrapper
                    text = text[3:-3].strip()
                
                return text
            return None
        except Exception as e:
            print(f"Gemini request error: {e}")
            return None

    def split_text_for_subtitle(self, text: str, max_len: int = 26) -> Optional[List[str]]:
        """
        Use LLM to split Japanese text into natural subtitle lines.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of 1-2 strings, or None if API fails
        """
        if not self.api_key:
            return None
            
        prompt = f"""あなたは日本語字幕の専門家です。以下のテキストを自然で読みやすい字幕に分割してください。

テキスト: {text}

分割要件:
• 各行: 最大{max_len}文字
• 最大2行まで
• 意味のまとまりを重視
• 「」内や数値+単位は分割禁止
• 自然な読みリズムを保持
• 文脈を失わない分割

出力形式（JSON）:
{{"lines": ["1行目", "2行目"]}}

単一行の場合:
{{"lines": ["単一行"]}}

例:
- 入力: "人工知能の発展により私たちの生活は大きく変化しています"
- 出力: {{"lines": ["人工知能の発展により", "私たちの生活は大きく変化しています"]}}"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "日本語字幕の専門家として、読みやすさと意味の保持を両立した自然な分割を行ってください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if "lines" in result and isinstance(result["lines"], list):
                # Validate line lengths
                lines = result["lines"]
                if all(len(line) <= max_len for line in lines) and len(lines) <= 2:
                    return lines
                    
        except json.JSONDecodeError as e:
            print(f"[WARN] LLM response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
        except Exception as e:
            print(f"[WARN] LLM text splitting failed: {e}")
            
        return None

    def split_text_for_multiple_subtitles(self, text: str, max_len: int = 26) -> Optional[List[List[str]]]:
        """
        Use LLM to split Japanese text into multiple subtitle cards.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of subtitle cards (each card has 1-2 lines), or None if API fails
        """
        if not self.api_key:
            return None
            
        prompt = f"""日本語字幕の専門家として、長いテキストを複数の字幕カードに分割してください。

テキスト: {text}

分割要件:
• 1カード = 最大2行、各行{max_len}文字以内
• 意味の完結性を重視（文脈を保持）
• 情報の省略・要約禁止（全内容を保持）
• 「」内、数値+単位、固有名詞は分割禁止
• 自然な読みリズムと理解しやすさ

出力形式（JSON）:
{{"cards": [
  ["カード1行1", "カード1行2"],
  ["カード2行1"],
  ["カード3行1", "カード3行2"]
]}}

例:
- 短文: {{"cards": [["短いテキスト"]]}}
- 長文: {{"cards": [["前半の意味", "まとまり"], ["後半の意味", "まとまり"]]}}

重要: 全ての情報を保持し、読みやすく分割してください。"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "日本語字幕の専門家として、全ての情報を保持しながら自然で理解しやすい分割を行ってください。省略は一切しないでください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if "cards" in result and isinstance(result["cards"], list):
                cards = result["cards"]
                # Validate each card
                valid_cards = []
                for card in cards:
                    if isinstance(card, list) and len(card) <= 2:
                        if all(isinstance(line, str) and len(line) <= max_len for line in card):
                            valid_cards.append(card)
                
                if valid_cards:
                    return valid_cards
                    
        except json.JSONDecodeError as e:
            print(f"[WARN] LLM multiple subtitle response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
        except Exception as e:
            print(f"[WARN] LLM multiple subtitle splitting failed: {e}")
            
        return None

    def split_text_to_cards(self, text: str, max_len: int = 26, max_lines_per_card: int = 2) -> Optional[List[List[str]]]:
        """
        Provider-agnostic subtitle card splitter with cost tracking.
        Tries CLI -> Claude -> Gemini -> OpenAI -> None.
        Returns list of cards (each 1-2 lines) or None.
        """
        # Build prompt shared across providers
        prompt = f"""あなたは日本語字幕の編集者です。以下のテキストを意味を失わずに自然な字幕カードに分割してください。

テキスト: {text}

要件:
• 1カード = 最大{max_lines_per_card}行、各行{max_len}文字以内
• 省略や要約は禁止。全情報を保持
• 自然な読点/語尾で折り返し、読みやすさ重視
• JSONのみを返す

出力形式（JSON）:
{{"cards": [["行1", "行2"], ["行1"], ["行1", "行2"]]}}
"""

        # Preferred path: respect provider setting
        print(f"[LLM] split_text_to_cards start provider={self.preferred_provider} len={len(text)} max_len={max_len}")
        _t0 = None
        try:
            import time as _time
            _t0 = _time.time()
        except Exception:
            pass
        if self.preferred_provider == 'cli' and self.cli_cmd:
            out = self._call_cli_json(prompt)
            if out:
                try:
                    data = json.loads(out)
                    cards = data.get("cards")
                    if isinstance(cards, list):
                        try:
                            rec = self.llm_cost.estimate("cli", "unknown", len(prompt), len(out))
                            self.last_cost = rec
                        except Exception:
                            pass
                        return cards
                except Exception as e:
                    print(f"CLI cards JSON parse error: {e}")

        if self.preferred_provider == 'claude_cli' and self.claude_code_available:
            out = self._call_claude_code(prompt)
            if out:
                try:
                    # Extract JSON substring
                    i, j = out.find('{'), out.rfind('}')
                    if i >= 0 and j > i:
                        json_text = out[i:j+1]
                        data = json.loads(json_text)
                        cards = data.get("cards")
                        if isinstance(cards, list):
                            try:
                                rec = self.llm_cost.estimate("claude", "unknown", len(prompt), len(json_text))
                                self.last_cost = rec
                            except Exception:
                                pass
                            return cards
                except Exception as e:
                    print(f"Claude cards JSON parse error: {e}")

        if self.preferred_provider == 'gemini' and self.gemini_api_key:
            out = self._generate_with_gemini(prompt)
            if out:
                try:
                    json_text = self._extract_json_object(out) or out
                    data = json.loads(json_text)
                    cards = data.get("cards")
                    if isinstance(cards, list):
                        try:
                            rec = self.llm_cost.estimate("gemini", self.gemini_model, len(prompt), len(json_text))
                            self.last_cost = rec
                        except Exception:
                            pass
                        return cards
                except Exception as e:
                    print(f"Gemini cards JSON parse error: {e}")
                    # Dump raw for debugging
                    try:
                        log_dir = Path("output/logs"); log_dir.mkdir(parents=True, exist_ok=True)
                        (log_dir / "llm_gemini_cards_error.json").write_text(out, encoding="utf-8")
                    except Exception:
                        pass

        if self.preferred_provider in ('openai','auto') and self.api_key and openai is not None:
            try:
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "日本語字幕の専門家として、自然で読みやすい字幕カード分割のみJSONで出力してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.2
                )
                content = response.choices[0].message.content.strip()
                data = json.loads(content)
                cards = data.get("cards")
                if isinstance(cards, list):
                    try:
                        rec = self.llm_cost.estimate("openai", self.model, len(prompt), len(content))
                        self.last_cost = rec
                    except Exception:
                        pass
                    return cards
            except Exception as e:
                print(f"OpenAI cards error: {e}")

        # Auto mode fallbacks if specific provider paths failed
        if self.preferred_provider == 'auto':
            # Try CLI
            if self.cli_cmd:
                out = self._call_cli_json(prompt)
                if out:
                    try:
                        data = json.loads(out)
                        cards = data.get("cards")
                        if isinstance(cards, list):
                            try:
                                rec = self.llm_cost.estimate("cli", "unknown", len(prompt), len(out))
                                self.last_cost = rec
                            except Exception:
                                pass
                            return cards
                    except Exception as e:
                        print(f"CLI cards JSON parse error: {e}")
            # Try Claude
            if self.claude_code_available:
                out = self._call_claude_code(prompt)
                if out:
                    try:
                        i, j = out.find('{'), out.rfind('}')
                        if i >= 0 and j > i:
                            json_text = out[i:j+1]
                            data = json.loads(json_text)
                            cards = data.get("cards")
                            if isinstance(cards, list):
                                try:
                                    rec = self.llm_cost.estimate("claude", "unknown", len(prompt), len(json_text))
                                    self.last_cost = rec
                                except Exception:
                                    pass
                                return cards
                    except Exception as e:
                        print(f"Claude cards JSON parse error: {e}")
            # Try Gemini
            if self.gemini_api_key:
                out = self._generate_with_gemini(prompt)
                if out:
                    try:
                        json_text = self._extract_json_object(out) or out
                        data = json.loads(json_text)
                        cards = data.get("cards")
                        if isinstance(cards, list):
                            try:
                                rec = self.llm_cost.estimate("gemini", self.gemini_model, len(prompt), len(json_text))
                                self.last_cost = rec
                            except Exception:
                                pass
                            return cards
                    except Exception as e:
                        print(f"Gemini cards JSON parse error: {e}")
                        try:
                            log_dir = Path("output/logs"); log_dir.mkdir(parents=True, exist_ok=True)
                            (log_dir / "llm_gemini_cards_error_auto.json").write_text(out, encoding="utf-8")
                        except Exception:
                            pass
        # Timing end
        try:
            if _t0 is not None:
                import time as _time
                print(f"[LLM] split_text_to_cards end elapsed={_time.time()-_t0:.2f}s -> None")
        except Exception:
            pass
        return None

    # === ElevenLabs v3 Audio-tag Enhancement ===
    def enhance_tts_with_eleven_v3(self, text: str, role: str = "NA", speaker: Optional[str] = None) -> Optional[str]:
        """
        Generate audio-tagged (ElevenLabs v3) performance text from a script line.

        Args:
            text: Original script line
            role: 'NA' (narration) or 'DL' (dialogue) or 'QT'
            speaker: Optional speaker name to prefix for dialogue

        Returns:
            Tag-enhanced text (plain string with tags) or None on failure
        """
        role = (role or "NA").upper()
        speaker_hint = (speaker or ("Narrator" if role == "NA" else "Speaker")).strip()
        # System + user prompt crafted for ElevenLabs v3 audio tags
        sys_prompt = (
            "あなたは音声演出家です。日本語台本に対し、ElevenLabs v3の音声タグを適切に挿入して、"
            "感情・間・非言語表現（息遣い・笑い等）を演出します。出力はテキストのみ。説明やJSONは不要。"
        )
        user_prompt = f"""
以下の台本行に、ElevenLabs v3で使用できる音声タグを付加してください。

ルール:
- <laugh>, <sigh>, <shout>, <whisper> などの非言語タグを必要に応じて挿入
- 感情・トーンを <emotional mood="...">〜</emotional> で包む（例: calm, excited, serious など）
- ナレーションは <narration>〜</narration> とし、落ち着いたトーン（calm）を基本に
- セリフ（対話）は行頭に話者名を付与（例: {speaker_hint}: ...）
- 原文の情報は省略せず保持。過剰な脚色は避ける
- 出力は音声タグ付きのテキストのみ（Markdownや説明は不要）

役割: {('ナレーション' if role=='NA' else 'セリフ')}
話者名: {speaker_hint}
テキスト: {text}
"""

        # Provider preference: try CLI, then Claude Code, then Gemini, then OpenAI
        # CLI
        if self.preferred_provider == 'cli' and self.cli_cmd:
            out = self._call_cli_json(user_prompt, system_prompt=sys_prompt)
            if out:
                return out.strip()

        # Claude Code (text output)
        if self.preferred_provider == 'claude_cli' and self.claude_code_available:
            out = self._call_claude_code(user_prompt, system_prompt=sys_prompt)
            if out:
                # Basic sanitization: strip code fences
                s = out.strip()
                if s.startswith('```') and s.endswith('```'):
                    s = s.split('\n', 1)[1].rsplit('\n', 1)[0]
                try:
                    rec = self.llm_cost.estimate("claude", "unknown", len(user_prompt), len(s))
                    self.last_cost = rec
                except Exception:
                    pass
                return s

        # Gemini
        if self.preferred_provider == 'gemini' and self.gemini_api_key:
            composed = f"System: {sys_prompt}\n\nUser: {user_prompt}"
            out = self._generate_with_gemini(composed)
            if out:
                s = (out or '').strip()
                # Remove Markdown fences if present
                if s.startswith('```') and s.endswith('```'):
                    s = s.split('\n', 1)[1].rsplit('\n', 1)[0]
                try:
                    rec = self.llm_cost.estimate("gemini", self.gemini_model, len(composed), len(s))
                    self.last_cost = rec
                except Exception:
                    pass
                return s

        # OpenAI fallback
        if (self.preferred_provider in ('openai', 'auto')) and (self.api_key and openai is not None):
            try:
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                s = response.choices[0].message.content.strip()
                # Strip fences if any
                if s.startswith('```') and s.endswith('```'):
                    s = s.split('\n', 1)[1].rsplit('\n', 1)[0]
                try:
                    rec = self.llm_cost.estimate("openai", self.model, len(user_prompt), len(s))
                    self.last_cost = rec
                except Exception:
                    pass
                return s
            except Exception as e:
                print(f"[WARN] OpenAI enhance_tts failed: {e}")

        return None

    def generate_storyboard(self, script_text: str, parsed_segments: List = None) -> Optional[dict]:
        """
        Generate storyboard with scene breakdown, shot descriptions, and stock keywords.
        
        Args:
            script_text: Japanese script text to analyze
            parsed_segments: Pre-analyzed script segments (optional)
            
        Returns:
            Dictionary with storyboard structure, or None if API fails
        """
        # Demo生成は無効化（LLM以外のロールバックを廃止）

        prompt = f"""あなたは映像制作の専門家です。以下の台本から文字コンテ（ストーリーボード）を生成してください。

台本:
{script_text}

要求:
1. 台本を意味的なシーンに分割
2. 各シーンの概要を1文で要約
3. 適切なショット（カメラアングル）を提案
4. 素材検索用のキーワードを英語・日本語で生成
5. AI画像生成用のプロンプトを作成

ショット記号:
- WS (Wide Shot): 全景・風景
- MS (Medium Shot): 中景・人物腰上
- CU (Close Up): クローズアップ・表情
- POV (Point of View): 主観ショット
- INSERT: 挿入カット・資料など

出力形式（JSON）:
{{
  "storyboard": [
    {{
      "scene_id": "SC-001",
      "outline": "シーンの1文要約",
      "shotlist": [
        {{"shot": "WS", "desc": "具体的なショット説明"}}
      ],
      "stock_keywords": ["english keyword", "japanese keyword", "concept"],
      "gen_prompts": ["AI画像生成用の詳細プロンプト"]
    }}
  ]
}}

注意:
- 各シーンは台本の自然な意味的区切りに従う
- ショット説明は具体的で映像的に
- キーワードは素材サイト検索に最適化
- プロンプトは高品質な画像生成を想定"""

        # Provider preference
        if self.preferred_provider == 'cli' and self.cli_cmd:
            response = self._call_cli_json(prompt)
            if response:
                try:
                    result = json.loads(response)
                    if "storyboard" in result and isinstance(result["storyboard"], list):
                        # Cost estimate (provider unknown CLI)
                        try:
                            rec = self.llm_cost.estimate("cli", "unknown", len(prompt), len(response))
                            self.last_cost = rec
                            print(f"[COST] LLM est (CLI): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                        except Exception:
                            pass
                        return result
                except Exception as e:
                    print(f"CLI JSON parse error: {e}")
        
        if self.preferred_provider == 'claude_cli' and self.claude_code_available:
            result = self._generate_storyboard_with_claude(script_text, parsed_segments)
            if result:
                # Rough cost estimate for Claude path (no usage data available)
                try:
                    prompt_chars = len(prompt)
                    completion_chars = len(json.dumps(result, ensure_ascii=False))
                    rec = self.llm_cost.estimate("claude", "unknown", prompt_chars, completion_chars)
                    self.last_cost = rec
                    print(f"[COST] LLM est (Claude): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                except Exception:
                    pass
                return result
            print("[WARN] Claude storyboard generation failed")
            return None

        if self.preferred_provider == 'gemini' and self.gemini_api_key:
            print("[LLM] generate_storyboard via Gemini")
            response = self._generate_with_gemini(prompt)
            if response:
                try:
                    json_text = self._extract_json_object(response) or response
                    result = json.loads(json_text)
                    if "storyboard" in result and isinstance(result["storyboard"], list):
                        try:
                            rec = self.llm_cost.estimate("gemini", self.gemini_model, len(prompt), len(json_text))
                            self.last_cost = rec
                            print(f"[COST] LLM est (Gemini): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                        except Exception:
                            pass
                        return result
                except Exception as e:
                    print(f"Gemini JSON parse error: {e}")
                    try:
                        log_dir = Path("output/logs"); log_dir.mkdir(parents=True, exist_ok=True)
                        (log_dir / "llm_gemini_storyboard_error.json").write_text(response, encoding="utf-8")
                    except Exception:
                        pass

        if self.preferred_provider == 'openai' and (not self.api_key or openai is None):
            return None
            
        try:
            # 'auto' mode will try OpenAI as a last resort
            if self.preferred_provider == 'openai' or (self.preferred_provider == 'auto' and self.api_key and openai is not None):
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "映像制作とストーリーボード作成の専門家として、実用的で詳細な文字コンテを作成してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                content = response.choices[0].message.content.strip()
                result = json.loads(content)
                
                if "storyboard" in result and isinstance(result["storyboard"], list):
                    # Cost estimate for OpenAI path
                    try:
                        rec = self.llm_cost.estimate("openai", self.model, len(prompt), len(content))
                        self.last_cost = rec
                        print(f"[COST] LLM est (OpenAI): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                    except Exception:
                        pass
                    return result
                print("[WARN] Storyboard response invalid")
                return None
            
            # If we are in 'auto' mode and got here, it means all preferred providers failed.
            # The logic above already tried OpenAI if it was available.
            if self.preferred_provider == 'auto':
                print("[WARN] All LLM providers failed for storyboard generation.")
                return None

        except json.JSONDecodeError as e:
            print(f"[WARN] Storyboard response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
            return None
        except Exception as e:
            print(f"[WARN] Storyboard generation failed: {e}")
            return None
        
        return None

    def generate_music_prompts(self, script_text: str, parsed_segments: List = None) -> Optional[dict]:
        """
        Generate BGM atmosphere descriptions and music prompts.
        
        Args:
            script_text: Japanese script text to analyze
            
        Returns:
            Dictionary with music prompts structure, or None if API fails
        """
        # Demo生成は無効化

        prompt = f"""あなたは音楽制作と映像音響の専門家です。以下の台本からBGM・音楽の雰囲気記述を生成してください。

台本:
{script_text}

要求:
1. 台本の内容・雰囲気に合ったBGMキューを提案
2. 各キューの感情・ムード・BPM・スタイルを指定
3. Suno AI等の音楽生成AIに適したプロンプト作成
4. 素材サイト検索用のキーワード生成

音楽スタイル例:
- ambient, cinematic, piano, strings, electronic
- uplifting, contemplative, mysterious, warm, energetic
- documentary style, meditation music, corporate

出力形式（JSON）:
{{
  "music_prompts": [
    {{
      "cue_id": "M-001",
      "mood": "warm introspective",
      "bpm": 78,
      "style": "ambient piano with subtle strings",
      "suno_prompt": "Gentle contemplative piano melody with warm ambient textures, soft string pads, 78 BPM, documentary style, meditation mood",
      "stock_keywords": ["contemplative piano", "ambient documentary", "meditation background"]
    }}
  ]
}}

注意:
- 台本の感情的な流れを音楽で表現
- 各キューは3-5分程度の楽曲を想定
- Suno AIプロンプトは具体的で詳細に
- キーワードは音楽素材サイト検索に最適化"""

        if self.preferred_provider == 'cli' and self.cli_cmd:
            response = self._call_cli_json(prompt)
            if response:
                try:
                    result = json.loads(response)
                    if "music_prompts" in result and isinstance(result["music_prompts"], list):
                        try:
                            rec = self.llm_cost.estimate("cli", "unknown", len(prompt), len(response))
                            self.last_cost = rec
                            print(f"[COST] LLM est (CLI): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                        except Exception:
                            pass
                        return result
                except Exception as e:
                    print(f"CLI JSON parse error: {e}")
        
        if self.preferred_provider == 'claude_cli' and self.claude_code_available:
            result = self._generate_music_prompts_with_claude(script_text, parsed_segments)
            if result:
                try:
                    prompt_chars = len(prompt)
                    completion_chars = len(json.dumps(result, ensure_ascii=False))
                    rec = self.llm_cost.estimate("claude", "unknown", prompt_chars, completion_chars)
                    self.last_cost = rec
                    print(f"[COST] LLM est (Claude): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                except Exception:
                    pass
                return result
            print("[WARN] Claude music prompts failed")
            return None

        if self.preferred_provider == 'gemini' and self.gemini_api_key:
            print("[LLM] generate_music_prompts via Gemini")
            response = self._generate_with_gemini(prompt)
            if response:
                try:
                    json_text = self._extract_json_object(response) or response
                    result = json.loads(json_text)
                    if "music_prompts" in result and isinstance(result["music_prompts"], list):
                        try:
                            rec = self.llm_cost.estimate("gemini", self.gemini_model, len(prompt), len(json_text))
                            self.last_cost = rec
                            print(f"[COST] LLM est (Gemini): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                        except Exception:
                            pass
                        return result
                except Exception as e:
                    print(f"Gemini JSON parse error: {e}")
                    try:
                        log_dir = Path("output/logs"); log_dir.mkdir(parents=True, exist_ok=True)
                        (log_dir / "llm_gemini_music_error.json").write_text(response, encoding="utf-8")
                    except Exception:
                        pass

        if self.preferred_provider == 'openai' and (not self.api_key or openai is None):
            return None
            
        try:
            if self.preferred_provider == 'openai' or (self.preferred_provider == 'auto' and self.api_key and openai is not None):
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "音楽制作と映像音響の専門家として、台本の感情的な流れに合った適切な音楽提案を行ってください。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.4
                )
                content = response.choices[0].message.content.strip()
                result = json.loads(content)
                
                if "music_prompts" in result and isinstance(result["music_prompts"], list):
                    try:
                        rec = self.llm_cost.estimate("openai", self.model, len(prompt), len(content))
                        self.last_cost = rec
                        print(f"[COST] LLM est (OpenAI): ¥{rec['cost_jpy']} (${rec['cost_usd']})")
                    except Exception:
                        pass
                    return result
                print("[WARN] Music prompts response invalid")
                return None
            
            if self.preferred_provider == 'auto':
                print("[WARN] All LLM providers failed for music prompt generation.")
                return None

        except json.JSONDecodeError as e:
            print(f"[WARN] Music prompts response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
            return None
        except Exception as e:
            print(f"[WARN] Music prompts generation failed: {e}")
            return None
        
        return None

    def _generate_demo_storyboard(self, script_text: str) -> dict:
        """デモ用文字コンテ生成"""
        # 台本の長さに応じてシーン数を決定
        lines = script_text.split('\n')
        scene_count = max(3, min(8, len(lines) // 3))
        
        scenes = []
        for i in range(scene_count):
            scene_id = f"SC-{i+1:03d}"
            
            if i == 0:
                outline = "オープニング・導入シーン"
                shot_desc = "書斎の全景、本棚と机"
                keywords = ["study room", "books library", "academic workspace", "書斎", "本棚", "学習環境"]
            elif i == scene_count - 1:
                outline = "まとめ・クロージング"
                shot_desc = "夕日の中の風景、希望的な雰囲気"
                keywords = ["sunset horizon", "hopeful future", "peaceful landscape", "夕日", "希望", "未来"]
            else:
                outline = f"メインコンテンツ - セクション {i}"
                shot_desc = f"専門家インタビュー、資料映像"
                keywords = ["expert interview", "documentary style", "professional portrait", "インタビュー", "専門家", "解説"]
            
            scenes.append({
                "scene_id": scene_id,
                "outline": outline,
                "shotlist": [{"shot": "WS" if i % 3 == 0 else "MS" if i % 3 == 1 else "CU", "desc": shot_desc}],
                "stock_keywords": keywords,
                "gen_prompts": [f"Professional {shot_desc.lower()}, documentary style, high quality, cinematic lighting"]
            })
        
        return {"storyboard": scenes}
    
    def _generate_demo_music_prompts(self, script_text: str) -> dict:
        """デモ用BGM雰囲気生成"""
        # 台本の雰囲気を簡易分析
        music_cues = []
        
        # 基本的なBGMキューを生成
        cues_data = [
            {
                "cue_id": "M-001",
                "mood": "contemplative and warm",
                "bpm": 72,
                "style": "ambient piano with subtle strings",
                "suno_prompt": "Gentle contemplative piano melody with warm ambient textures, soft string pads, 72 BPM, documentary style, introspective mood",
                "stock_keywords": ["contemplative piano", "ambient documentary", "warm introspective"]
            },
            {
                "cue_id": "M-002", 
                "mood": "inspiring and uplifting",
                "bpm": 85,
                "style": "orchestral with piano lead",
                "suno_prompt": "Inspiring orchestral arrangement with piano melody, building emotional crescendo, 85 BPM, hopeful and uplifting",
                "stock_keywords": ["inspiring orchestral", "uplifting piano", "emotional crescendo"]
            },
            {
                "cue_id": "M-003",
                "mood": "peaceful resolution",
                "bpm": 65,
                "style": "solo piano with ambient pad",
                "suno_prompt": "Peaceful solo piano with gentle ambient background, resolution and closure feeling, 65 BPM, calming finish",
                "stock_keywords": ["peaceful piano", "ambient resolution", "calming outro"]
            }
        ]
        
        return {"music_prompts": cues_data}

    def _generate_storyboard_with_claude(self, script_text: str, parsed_segments: List = None) -> Optional[dict]:
        """Claude Codeを使って文字コンテ生成（解析結果連携版）"""
        system_prompt = """あなたは映像制作の専門家です。台本解析結果を活用して高品質な文字コンテ（ストーリーボード）を生成してください。

ショット記号:
- WS (Wide Shot): 全景・風景・環境ショット
- MS (Medium Shot): 中景・人物腰上・インタビュー
- CU (Close Up): クローズアップ・表情・重要な詳細
- POV (Point of View): 主観ショット・視点切り替え
- INSERT: 挿入カット・資料・グラフィック

話者タイプ別ショット提案:
- ナレーション(NA): WS環境ショット、INSERT資料映像が効果的
- 対話・セリフ(DL): MS人物ショット、CU表情ショットが効果的
- CPS高速(>10): 短いカット、シンプルな映像構成が推奨

必ずJSON形式で回答してください。"""

        # セグメント解析結果を含めたプロンプト構築
        analysis_info = ""
        if parsed_segments:
            analysis_info = "\n\n## 台本解析結果（参考情報）:\n"
            for i, segment in enumerate(parsed_segments[:10], 1):  # 最初の10セグメントのみ
                speaker = getattr(segment, 'speaker_type', 'UNKNOWN')
                text = getattr(segment, 'text', '')[:100]  # 最初の100文字
                analysis_info += f"セグメント{i}: [{speaker.value if hasattr(speaker, 'value') else speaker}] {text}...\n"
            analysis_info += "\n※ この解析結果を参考に、話者タイプに応じた適切なショット構成を提案してください。"

        prompt = f"""以下の台本から文字コンテを生成してください：

台本:
{script_text}{analysis_info}

要求:
1. 台本を意味的なシーンに分割
2. 各シーンの概要を1文で要約
3. 適切なショット（カメラアングル）を提案
4. 素材検索用のキーワードを英語・日本語で生成
5. AI画像生成用のプロンプトを作成

出力形式（JSON）:
{{
  "storyboard": [
    {{
      "scene_id": "SC-001",
      "outline": "シーンの1文要約",
      "shotlist": [
        {{"shot": "WS", "desc": "具体的なショット説明"}}
      ],
      "stock_keywords": ["english keyword", "japanese keyword", "concept"],
      "gen_prompts": ["AI画像生成用の詳細プロンプト"]
    }}
  ]
}}"""

        response = self._call_claude_code(prompt, system_prompt)
        if response:
            try:
                # JSONレスポンスをパース
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response[json_start:json_end]
                    return json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"Claude Code JSON parse error: {e}")
                return None
        
        return None

    def _generate_music_prompts_with_claude(self, script_text: str, parsed_segments: List = None) -> Optional[dict]:
        """Claude Codeを使ってBGM雰囲気生成（解析結果連携版）"""
        system_prompt = """あなたは音楽制作と映像音響の専門家です。台本解析結果を活用してBGM・音楽の雰囲気記述を生成してください。

音楽スタイル例:
- ambient, cinematic, piano, strings, electronic
- uplifting, contemplative, mysterious, warm, energetic
- documentary style, meditation music, corporate

話者タイプ別音楽提案:
- ナレーション(NA)主体: アンビエント、ドキュメンタリー調、穏やかな楽器
- 対話・セリフ(DL)多め: 感情表現豊か、ドラマチック、キャラクター性重視
- CPS高速部分: シンプルな音楽、邪魔しないBGM

必ずJSON形式で回答してください。"""

        # セグメント解析結果を含めたプロンプト構築
        analysis_info = ""
        if parsed_segments:
            na_count = sum(1 for seg in parsed_segments if getattr(seg, 'speaker_type', '') == 'NARRATOR' or str(getattr(seg, 'speaker_type', '')).endswith('NA'))
            dl_count = sum(1 for seg in parsed_segments if getattr(seg, 'speaker_type', '') == 'DIALOGUE' or str(getattr(seg, 'speaker_type', '')).endswith('DL'))
            total_segments = len(parsed_segments)
            
            analysis_info = f"""

## 台本解析結果（参考情報）:
- 総セグメント数: {total_segments}
- ナレーション(NA): {na_count}セグメント ({na_count/total_segments*100:.1f}%)
- 対話・セリフ(DL): {dl_count}セグメント ({dl_count/total_segments*100:.1f}%)

※ この分析結果を参考に、ナレーション主体かセリフ主体かに応じた音楽構成を提案してください。"""

        prompt = f"""以下の台本からBGM雰囲気記述を生成してください：

台本:
{script_text}{analysis_info}

要求:
1. 台本の内容・雰囲気に合ったBGMキューを提案
2. 各キューの感情・ムード・BPM・スタイルを指定
3. Suno AI等の音楽生成AIに適したプロンプト作成
4. 素材サイト検索用のキーワード生成

出力形式（JSON）:
{{
  "music_prompts": [
    {{
      "cue_id": "M-001",
      "mood": "warm introspective",
      "bpm": 78,
      "style": "ambient piano with subtle strings",
      "suno_prompt": "Gentle contemplative piano melody with warm ambient textures, soft string pads, 78 BPM, documentary style, meditation mood",
      "stock_keywords": ["contemplative piano", "ambient documentary", "meditation background"]
    }}
  ]
}}"""

        response = self._call_claude_code(prompt, system_prompt)
        if response:
            try:
                # JSONレスポンスをパース
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response[json_start:json_end]
                    return json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"Claude Code JSON parse error: {e}")
                return None
        
        return None

    def generate(self, prompt: str, script_text: str):
        # 実際はOpenAI/Claude API呼び出しに差し替え
        return {
            "narration": [{"id":"NA-001","text":"人はなぜ学ぶのか。"}],
            "dialogues": [{"id":"DL-001","speaker":"人物A","text":"きっかけは写真でした。"}],
            "subtitles": [{"id":"SB-001","text_2line":["人はなぜ学ぶのか、","忙しい日常の中で。"]}]
        }
