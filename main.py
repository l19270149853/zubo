import os
import re
import socket
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_base_urls():
    """智能获取基础URL（增强版）"""
    base_urls = set()
    
    # 本地文件解析（支持多种格式）
    local_pattern = re.compile(
        r'(https?://[\w\.-]+(?::\d+)?)/?',  # 匹配含端口号和无端口的情况
        re.IGNORECASE
    )
    try:
        if os.path.exists('gdzb.txt'):
            with open('gdzb.txt', 'r', encoding='utf-8') as f:
                content = f.read()
                urls = local_pattern.findall(content)
                base_urls.update(urls)
                print(f"✅ 从本地文件发现 {len(urls)} 个有效URL")
    except Exception as e:
        print(f"⚠️ 本地文件读取异常: {str(e)}")

    # 远程文件解析（带重试机制）
    try:
        for _ in range(3):  # 最多重试3次
            try:
                response = requests.get(
                    'https://d.kstore.dev/download/10694/%E6%97%A7%E6%96%87%E4%BB%B6/%E7%BB%84%E6%92%ADId/gdcn.txt',
                    timeout=15
                )
                remote_urls = local_pattern.findall(response.text)
                new_urls = [url for url in remote_urls if url not in base_urls]
                base_urls.update(remote_urls)
                print(f"🌐 远程获取新增 {len(new_urls)} 个URL")
                break
            except requests.exceptions.RequestException as e:
                print(f"⏳ 远程获取失败，正在重试... ({str(e)})")
                time.sleep(5)
    except Exception as e:
        print(f"❌ 最终远程获取失败: {str(e)}")

    return list(base_urls)

def udp_port_check(url):
    """精准UDP端口检测（带详细状态反馈）"""
    try:
        # 解析URL结构
        match = re.match(r'http://([^/:]+):?(\d+)?/', url)
        if not match:
            print(f"⛔ 无效URL格式: {url}")
            return None
        
        host = match.group(1)
        port = int(match.group(2)) if match.group(2) else 80
        test_port = 5146  # 目标UDP端口
        
        # 创建UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(3)  # 3秒超时
            start_time = time.time()
            
            # 发送空数据包
            s.sendto(b'', (host, test_port))
            
            # 尝试接收响应（部分服务会有响应）
            try:
                data, addr = s.recvfrom(1024)
                print(f"🔔 {url} 收到响应 ({len(data)}字节)")
                return url
            except socket.timeout:
                # 没有响应不代表不可用，记录连接成功
                print(f"⌛ {url} 端口可达（无响应）")
                return url
                
    except Exception as e:
        print(f"❌ 检测失败 {url}: {str(e)}")
        return None

def generate_final_list(valid_urls):
    """生成最终播放列表（带完整性校验）"""
    final_content = []
    
    # 确保gdNet.txt存在
    if not os.path.exists('gdNet.txt'):
        print("❌ 关键文件gdNet.txt缺失！")
        return []
    
    # 解析频道列表
    channel_pattern = re.compile(
        r'^(.*?),\s*rtp://(\d+\.\d+\.\d+\.\d+:\d+)$',
        re.MULTILINE
    )
    
    try:
        with open('gdNet.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            matches = channel_pattern.findall(content)
            
            if not matches:
                print("⚠️ gdNet.txt格式异常，请检查文件内容！")
                return []
            
            print(f"📺 发现 {len(matches)} 个电视频道")
            
            # 生成所有有效组合
            for name, ip_port in matches:
                for base_url in valid_urls:
                    entry = f"{name},{base_url}udp/{ip_port}"
                    final_content.append(entry)
                    print(f"✨ 生成条目: {entry}")
                    
    except Exception as e:
        print(f"❌ 文件处理异常: {str(e)}")
    
    return final_content

def git_operations():
    """安全的Git操作（自动适配分支）"""
    try:
        # 获取当前分支名称
        branch = os.popen('git symbolic-ref --short HEAD').read().strip()
        print(f"🌿 当前分支: {branch}")
        
        # 配置Git
        os.system('git config --global user.name "l19270149853"')
        os.system('git config --global user.email "362213335lkh@gmail.com"')
        
        # 添加提交
        os.system('git add gdzb.txt')
        commit_cmd = f'git commit -m "自动更新直播源 {time.strftime("%Y-%m-%d %H:%M")}"'
        os.system(commit_cmd)
        
        # 智能推送
        push_cmd = f'git push origin {branch} --force-with-lease'
        push_result = os.system(push_cmd)
        if push_result == 0:
            print("🚀 推送成功！")
        else:
            print("⚠️ 推送失败，请检查权限或远程仓库状态")
    except Exception as e:
        print(f"❌ Git操作异常: {str(e)}")

def main():
    print("🚦 开始执行直播源更新流程")
    
    # 步骤1：获取基础URL
    base_urls = fetch_base_urls()
    print(f"🔍 总发现 {len(base_urls)} 个候选URL")
    
    # 步骤2：精准检测有效URL
    valid_urls = []
    with ThreadPoolExecutor(max_workers=20) as executor:  # 增加并发数
        futures = {executor.submit(udp_port_check, url): url for url in base_urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_urls.append(result)
                print(f"✅ 验证通过: {result}")
    
    print(f"🏆 最终有效URL数量: {len(valid_urls)}")
    
    # 步骤3：生成最终列表
    final_content = generate_final_list(valid_urls)
    
    # 步骤4：写入文件
    if final_content:
        with open('gdzb.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(final_content))
        print(f"💾 成功写入 {len(final_content)} 条记录到gdzb.txt")
        
        # 步骤5：Git操作
        if 'GITHUB_ACTIONS' in os.environ:
            git_operations()
    else:
        print("⚠️ 无有效数据，跳过文件写入")

if __name__ == '__main__':
    main()
