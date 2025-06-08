import requests
import sqlite3
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from datetime import datetime
import time
from rich.console import Console
from rich.table import Table

# 初始化控制台输出
console = Console()

def log_time(message, start_time=None):
    """记录时间并计算耗时"""
    current_time = time.time()
    if start_time:
        duration = round(current_time - start_time, 3)
        console.print(f"[dim]{message}: {duration} 秒[/]")
    return current_time

# ================== 配置部分 ==================
# Embedding API 配置
EMBEDDING_API_URL = "https://api.siliconflow.cn/v1/embeddings"
EMBEDDING_API_KEY = "sk-ifgpxfjzxudveescygugsurukwmbwzksckutynsbbwlgibrw"  # 替换为你的真实Key
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
EMBEDDING_DIMENSION = 1024  # 添加维度配置

# 对话API配置
CHAT_API_KEY = "sk-ifgpxfjzxudveescygugsurukwmbwzksckutynsbbwlgibrw"
CHAT_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"

# 数据库配置
DB_PATH = "knowledge_base.db"

# ================== 核心功能 ==================
class KnowledgeBase:
    def __init__(self):
        # 初始化数据库
        self.conn = sqlite3.connect(DB_PATH)
        self._init_db()
        
        # 初始化对话客户端
        self.chat_client = OpenAI(
            base_url='https://api.siliconflow.cn/v1',
            api_key=CHAT_API_KEY
        )

    def _init_db(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()
        
        # 检查数据库中的记录数
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        count = cursor.fetchone()[0]
        console.print(f"[yellow]当前知识库中有 {count} 条记录[/]")
        
        # 如果数据库为空，清空表并重新创建
        if count > 0:
            console.print("[yellow]检测到数据库中有记录，将清空并重新创建...[/]")
            cursor.execute("DROP TABLE knowledge")
            cursor.execute("""
            CREATE TABLE knowledge (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            self.conn.commit()
            console.print("[green]数据库已重置[/]")

    def add_knowledge(self, text):
        """添加知识文本并生成Embedding"""
        start_time = time.time()
        console.print(f"[yellow]开始添加知识: {text[:50]}...[/]")
        
        # 调用Embedding API
        headers = {
            "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": EMBEDDING_MODEL,
            "input": text,
            "encoding_format": "float"
        }
        
        embedding_start = time.time()
        response = requests.post(EMBEDDING_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            console.print(f"[red]Embedding API 调用失败: {response.text}[/]")
            return
            
        embedding = response.json()["data"][0]["embedding"]
        embedding_array = np.array(embedding, dtype=np.float32)
        
        # 验证向量维度
        if embedding_array.shape[0] != EMBEDDING_DIMENSION:
            console.print(f"[red]警告：向量维度不匹配 - 期望: {EMBEDDING_DIMENSION}, 实际: {embedding_array.shape[0]}[/]")
            return
            
        log_time("Embedding API调用耗时", embedding_start)
        
        # 存入数据库
        db_start = time.time()
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO knowledge (text, embedding) VALUES (?, ?)",
                (text, embedding_array.tobytes())
            )
            self.conn.commit()
            console.print(f"[green]成功添加知识，ID: {cursor.lastrowid}[/]")
        except Exception as e:
            console.print(f"[red]数据库存储失败: {str(e)}[/]")
            return
        log_time("数据库存储耗时", db_start)
        
        log_time("知识添加总耗时", start_time)

    def search_similar(self, query, top_k=3):
        """语义搜索最相关的知识"""
        start_time = time.time()
        console.print("[yellow]开始语义搜索...[/]")
        
        # 生成查询文本的Embedding
        embedding_start = time.time()
        headers = {
            "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": EMBEDDING_MODEL,
            "input": query,
            "encoding_format": "float"
        }
        response = requests.post(EMBEDDING_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            console.print(f"[red]Embedding API 调用失败: {response.text}[/]")
            return []
            
        query_embedding = np.array(response.json()["data"][0]["embedding"], dtype=np.float32)
        log_time("查询Embedding生成耗时", embedding_start)

        # 确保查询向量是有效的
        if np.isnan(query_embedding).any():
            console.print("[red]警告：查询向量包含无效值，将返回空结果[/]")
            return []

        # 从数据库读取所有知识
        db_start = time.time()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, text, embedding FROM knowledge")
        results = []
        
        similarity_start = time.time()
        for row in cursor.fetchall():
            try:
                # 从字节数据重建numpy数组
                vec = np.frombuffer(row[2], dtype=np.float32)
                
                # 确保向量维度匹配
                if vec.shape != query_embedding.shape:
                    console.print(f"[red]警告：向量维度不匹配 - 查询: {query_embedding.shape}, 知识: {vec.shape}[/]")
                    continue
                    
                # 计算余弦相似度
                dot_product = np.dot(query_embedding, vec)
                norm_query = np.linalg.norm(query_embedding)
                norm_vec = np.linalg.norm(vec)
                
                # 避免除以零
                if norm_query == 0 or norm_vec == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_query * norm_vec)
                
                console.print(f"[dim]ID {row[0]} 相似度: {similarity:.4f}[/]")
                
                if not np.isnan(similarity):
                    results.append((row[0], row[1], similarity))
            except Exception as e:
                console.print(f"[red]警告：处理向量时出错 - {str(e)}[/]")
                continue
        
        log_time("相似度计算耗时", similarity_start)
        log_time("数据库查询耗时", db_start)
        
        # 按相似度排序
        results.sort(key=lambda x: x[2], reverse=True)
        
        # 如果没有找到任何结果，返回所有知识
        if not results:
            console.print("[yellow]没有找到相似度大于0的结果，返回所有知识[/]")
            cursor.execute("SELECT id, text FROM knowledge")
            for row in cursor.fetchall():
                results.append((row[0], row[1], 0.0))
        
        log_time("语义搜索总耗时", start_time)
        return results[:top_k]

    def chat_with_context(self, query):
        """结合本地知识的智能对话"""
        start_time = time.time()
        console.print("[yellow]开始处理对话请求...[/]")
        
        # 1. 语义搜索相关上下文
        search_start = time.time()
        context = self.search_similar(query)
        console.print("\n[yellow]找到的相关知识：[/]")
        for item in context:
            console.print(f"[dim]相似度: {item[2]:.4f} - {item[1]}[/]")
        
        context_text = "\n".join([f"[知识ID:{item[0]}] {item[1]}" for item in context])
        log_time("上下文搜索耗时", search_start)
        
        # 2. 构建带上下文的对话提示
        prompt = f"""你是一个智能助手，需要根据以下已知信息回答问题。如果问题与已知信息无关，请明确告知用户。

已知信息：
{context_text}

用户问题：{query}

请基于上述已知信息回答问题。如果问题与已知信息无关，请直接说明"抱歉，我没有找到相关的信息"。不要编造或推测信息。"""

        # 打印发送给AI的完整信息
        console.print("\n[yellow]发送给AI的完整信息：[/]")
        console.print("[dim]" + "="*50 + "[/]")
        console.print("[dim]系统提示：[/]")
        console.print("[dim]你是一个智能助手，需要严格基于提供的上下文信息回答问题。如果问题与上下文无关，请明确告知用户。[/]")
        console.print("[dim]" + "-"*50 + "[/]")
        console.print("[dim]用户提示：[/]")
        console.print(f"[dim]{prompt}[/]")
        console.print("[dim]" + "="*50 + "[/]")
        
        # 3. 调用对话API
        chat_start = time.time()
        console.print("\n[yellow]开始调用对话API...[/]")
        response = self.chat_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能助手，需要严格基于提供的上下文信息回答问题。如果问题与上下文无关，请明确告知用户。"},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        
        # 流式输出结果
        first_chunk_time = None
        total_chunks = 0
        total_content_length = 0
        
        console.print("\n[yellow]开始接收响应...[/]")
        console.print(f"\n[回答] ", end="")
        for chunk in response:
            if not chunk.choices:
                continue
                
            if first_chunk_time is None:
                first_chunk_time = log_time("第一个响应块耗时", chat_start)
            
            total_chunks += 1
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                total_content_length += len(content)
                print(content, end="", flush=True)
            if chunk.choices[0].delta.reasoning_content:
                content = chunk.choices[0].delta.reasoning_content
                total_content_length += len(content)
                print(content, end="", flush=True)
        
        if total_chunks > 0:
            console.print(f"\n[dim]总响应块数: {total_chunks}[/]")
            console.print(f"[dim]总内容长度: {total_content_length} 字符[/]")
            console.print(f"[dim]平均每块耗时: {round((time.time() - first_chunk_time) / total_chunks, 3)} 秒[/]")
            console.print(f"[dim]平均每字符耗时: {round((time.time() - first_chunk_time) / total_content_length, 3)} 秒[/]")
        
        log_time("对话API总耗时", chat_start)
        log_time("对话处理总耗时", start_time)

# ================== 使用示例 ==================
if __name__ == "__main__":
    start_time = time.time()
    console.print(f"[bold green]开始执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    
    kb = KnowledgeBase()
    
    # 示例：添加知识库（实际使用时可以批量导入）
    kb.add_knowledge("工具猿网站，一个致力于为广大开发者和技术爱好者提供丰富工具资源的专业平台。在这里，我们不仅收集了各类实用工具，还对这些工具进行了细致整理与深入分析，旨在帮助用户高效解决问题、提升工作效率，并促进技术交流与发展。")
    kb.add_knowledge("牙合是一个位于中国深圳的AI公司，专注于AI技术的研发和应用。")
    
    # 显示所有知识
    cursor = kb.conn.cursor()
    cursor.execute("SELECT id, text FROM knowledge")
    console.print("\n[yellow]当前知识库中的所有内容：[/]")
    for row in cursor.fetchall():
        console.print(f"[dim]ID: {row[0]} - {row[1][:100]}...[/]")
    
    # 交互式对话
    while True:
        print("\n" + "="*50)
        query = input("\n请输入问题（输入q退出）: ").strip()
        if query.lower() == 'q':
            break
            
        query_start = time.time()
        kb.chat_with_context(query)
        log_time("问题处理总耗时", query_start)
    
    end_time = time.time()
    console.print(f"\n[bold green]执行完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    console.print(f"[bold cyan]总运行时间: {round(end_time - start_time, 3)} 秒[/]")