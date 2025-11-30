#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitee Issues 到 Jekyll 文章生成器
从指定的Gitee仓库issues中获取内容，自动生成Jekyll格式的文章
"""

import os
import re
import json
import requests
import datetime
from pathlib import Path
from urllib.parse import urlparse

class GiteeArticleGenerator:
    def __init__(self):
        self.base_url = "https://gitee.com/api/v5"
        self.repo_owner = "aywlzj"
        self.repo_name = "aywlzj.gitee.io"
        self.posts_dir = Path(__file__).parent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Gitee Article Generator/1.0'
        })
    
    def get_all_issues(self):
        """获取所有issues"""
        print(f"正在获取 {self.repo_owner}/{self.repo_name} 的所有issues...")
        
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
        params = {
            'state': 'all',  # 获取所有状态的issues
            'sort': 'created',
            'direction': 'asc',
            'per_page': 100
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            issues = response.json()
            print(f"成功获取 {len(issues)} 个issues")
            return issues
        except requests.exceptions.RequestException as e:
            print(f"获取issues失败: {e}")
            return []
    
    def get_issue_content(self, issue_number):
        """获取issue的详细内容（包含body）"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            issue = response.json()
            return issue
        except requests.exceptions.RequestException as e:
            print(f"获取issue {issue_number} 内容失败: {e}")
            return None
    
    def sanitize_filename(self, title):
        """将标题转换为安全的文件名"""
        # 移除或替换不安全的字符
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '-', filename)  # 空格替换为短横线
        filename = re.sub(r'-+', '-', filename)   # 多个短横线替换为一个
        filename = filename.strip('-')  # 移除首尾的短横线
        
        # 确保文件名不为空
        if not filename:
            filename = f"article-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        return filename
    
    def convert_to_jekyll_post(self, issue):
        """将issue转换为Jekyll文章格式"""
        # 提取issue信息
        title = issue['title']
        body = issue.get('body', '') or ''
        created_at = issue['created_at']
        updated_at = issue.get('updated_at', created_at)
        number = issue.get('number', '')
        
        # 解析日期
        created_date = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        updated_date = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        # 生成文件名
        date_str = created_date.strftime('%Y-%m-%d')
        safe_title = self.sanitize_filename(title)
        filename = f"{date_str}-{safe_title}.md"
        
        # 生成front matter
        front_matter = f"""---
title: "{title}"
date: {created_date.strftime('%Y-%m-%d %H:%M:%S %z')}
last_modified_at: {updated_date.strftime('%Y-%m-%d %H:%M:%S %z')}
categories: [Gitee Issues]
tags: [{number}]  # 使用issue编号作为tag
comments: true
---

## 原始链接

本文档从Gitee Issue自动生成，原文地址：[Issue #{number}](https://gitee.com/{self.repo_owner}/{self.repo_name}/issues/{number})

---

"""
        
        # 处理body内容（如果为空则使用标题作为内容）
        if not body.strip():
            content = f"**{title}**\n\n> 此文章来自Gitee Issue，内容为空，已自动使用标题作为内容。"
        else:
            # 处理markdown内容
            content = self.process_markdown(body)
        
        # 组合完整的文章内容
        article_content = front_matter + content
        
        return filename, article_content
    
    def process_markdown(self, markdown_content):
        """处理markdown内容，适配Jekyll"""
        if not markdown_content:
            return ""
        
        # 基本的markdown处理
        lines = markdown_content.split('\n')
        processed_lines = []
        
        for line in lines:
            # 移除Gitee特有的markdown语法（如果存在）
            line = re.sub(r'!\[.*?\]\(.*?\)', '', line)  # 临时移除图片，避免链接问题
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def save_article(self, filename, content):
        """保存文章到文件"""
        try:
            filepath = self.posts_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 成功生成文章: {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存文章失败 {filename}: {e}")
            return False
    
    def generate_articles(self):
        """主函数：生成所有文章"""
        print("🚀 开始从Gitee Issues生成Jekyll文章...")
        print("=" * 50)
        
        # 获取所有issues
        issues = self.get_all_issues()
        if not issues:
            print("没有获取到任何issues，程序退出")
            return
        
        generated_count = 0
        
        for issue in issues:
            number = issue.get('number')
            if not number:
                continue
            
            print(f"\n📝 处理Issue #{number}: {issue['title'][:50]}...")
            
            # 获取issue的详细内容
            issue_detail = self.get_issue_content(number)
            if not issue_detail:
                continue
            
            # 转换为Jekyll文章
            filename, content = self.convert_to_jekyll_post(issue_detail)
            
            # 检查文件是否已存在
            filepath = self.posts_dir / filename
            if filepath.exists():
                print(f"⚠️  文章已存在，跳过: {filename}")
                continue
            
            # 保存文章
            if self.save_article(filename, content):
                generated_count += 1
        
        print("\n" + "=" * 50)
        print(f"🎉 文章生成完成！共生成 {generated_count} 篇文章")
        print(f"📁 文章保存位置: {self.posts_dir}")
        
        # 显示生成的文章列表
        md_files = list(self.posts_dir.glob("*.md"))
        if md_files:
            print(f"\n📚 当前目录下的所有文章 ({len(md_files)} 篇):")
            for md_file in sorted(md_files):
                print(f"  - {md_file.name}")

def main():
    """主函数"""
    generator = GiteeArticleGenerator()
    generator.generate_articles()

if __name__ == "__main__":
    main()