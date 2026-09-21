<#
输入：RepositoryName（要新建的仓库名）、ExpectedOwner（预期的 GitHub 账号）。
输出：创建后的仓库地址和已验证的 HTTPS Pages 地址；失败时退出并保留错误。
功能：在用户自己的 GitHub CLI 登录环境下，新建公开仓库、提交完整源码、开启 Pages。
      不读取 DeepSeek Key、不覆盖已有仓库、不上传 .env 或本机录音。
#>
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$')]
    [string]$RepositoryName = 'fluffy-cat-journal',
    [ValidatePattern('^[A-Za-z0-9-]+$')]
    [string]$ExpectedOwner = 'ChiZhang-805'
)
$ErrorActionPreference = 'Stop'
$script:Root = $PSScriptRoot
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $script:Utf8
$OutputEncoding = $script:Utf8
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

<#
输入：无。
输出：GitHub CLI 可执行文件的绝对路径。
功能：从 PATH 和标准安装目录查找 gh；缺少时让用户确认后通过 winget 安装。
#>
function Find-GitHubCli {
    $found = Get-Command gh -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    foreach ($path in @("$env:ProgramFiles\GitHub CLI\gh.exe", "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe")) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw '请先从 https://cli.github.com 安装 GitHub CLI，再运行本文件。'
    }
    $answer = Read-Host '缺少 GitHub CLI。是否通过 winget 安装？输入 Y 继续'
    if ($answer -ne 'Y') { throw '已停止，没有创建仓库。' }
    & winget install --id GitHub.cli --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI 未安装成功。' }
    foreach ($path in @("$env:ProgramFiles\GitHub CLI\gh.exe", "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe")) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    throw '安装完成后请重新打开此脚本，以载入新的 PATH。'
}

<#
输入：Method（GET/POST/PATCH/PUT）、Path（GitHub API 路径）、Body（可选 JSON 对象）。
输出：GitHub 返回的 JSON 对象，空响应返回 null。
功能：通过 gh 已有登录发送 API 请求；不读取或打印 GitHub 令牌。
#>
function Invoke-GitHubApi {
    param([string]$Method, [string]$Path, $Body = $null)
    $inputFile = [IO.Path]::GetTempFileName()
    $errorFile = [IO.Path]::GetTempFileName()
    try {
        # 阶段一：以 UTF-8 文件传递 JSON，避免 Windows 管道损坏中文注释。
        $arguments = @('api', '--hostname', 'github.com', '--method', $Method, $Path,
            '-H', 'Accept: application/vnd.github+json', '-H', 'X-GitHub-Api-Version: 2022-11-28')
        if ($null -ne $Body) {
            $json = ConvertTo-Json -InputObject $Body -Depth 40 -Compress
            [IO.File]::WriteAllText($inputFile, $json, $script:Utf8)
            $arguments += @('--input', $inputFile)
        }
        # 阶段二：不手工处理授权头，交由 GitHub CLI 使用用户自己的登录凭据。
        $output = & $script:Gh @arguments 2> $errorFile
        if ($LASTEXITCODE -ne 0) {
            $detail = [IO.File]::ReadAllText($errorFile)
            throw "GitHub 请求失败：$Method $Path`n$detail"
        }
        $text = ($output -join "`n").Trim()
        if (-not $text) { return $null }
        return ConvertFrom-Json -InputObject $text
    } finally {
        Remove-Item -LiteralPath $inputFile, $errorFile -Force -ErrorAction SilentlyContinue
    }
}

<#
输入：无。
输出：仅属于项目源码的文件列表。
功能：使用白名单选择发布文件，拒绝符号链接；不扫描用户的其他目录或上传个人数据。
#>
function Get-PublishFiles {
    $files = New-Object 'System.Collections.Generic.List[System.IO.FileInfo]'
    foreach ($name in @('index.html', '.nojekyll', '.gitignore', 'README.md', 'publish.ps1', 'Publish-GitHub-Pages.cmd', 'package.json')) {
        $item = Get-Item -LiteralPath (Join-Path $script:Root $name) -Force
        $files.Add($item)
    }
    foreach ($folder in @('js', 'css', 'assets', 'tests')) {
        $directory = Join-Path $script:Root $folder
        if ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '发布目录不能是符号链接。' }
        foreach ($file in (Get-ChildItem -LiteralPath $directory -File -Recurse -Force)) {
            if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '不能发布符号链接。' }
            if ($file.Name -match '^\.|\.pyc$|report|results|\.png$' -and $folder -eq 'tests') { continue }
            if ($file.Name -match '^\.env|secret|credential|deployment-result') { continue }
            $files.Add($file)
        }
    }
    return $files.ToArray()
}

<#
输入：FullName（新建仓库的 owner/name）、Files（源码白名单）、Branch（默认分支）。
输出：提交 SHA。
功能：二进制素材上传为 blob，文本以内联 tree 提交，最后一次性移动分支指针。
#>
function Push-Source {
    param([string]$FullName, [object[]]$Files, [string]$Branch)
    # 阶段一：等待 GitHub 完成新仓库的初始化提交。
    $reference = $null
    for ($i = 0; $i -lt 10; $i++) {
        try { $reference = Invoke-GitHubApi 'GET' "repos/$FullName/git/ref/heads/$Branch"; break }
        catch { if ($i -eq 9) { throw }; Start-Sleep -Seconds 2 }
    }
    $parent = Invoke-GitHubApi 'GET' "repos/$FullName/git/commits/$($reference.object.sha)"
    $tree = New-Object 'System.Collections.Generic.List[object]'
    # 阶段二：只上传包内的静态源码；API Key 由用户之后在网页填写，不属于源码。
    foreach ($file in $Files) {
        $relative = $file.FullName.Substring($script:Root.Length).TrimStart([char[]]"\/").Replace('\', '/')
        Write-Host "  上传 $relative"
        if ($file.Extension -match '^\.(png|webp|gif|jpg|jpeg|ico)$') {
            $blob = Invoke-GitHubApi 'POST' "repos/$FullName/git/blobs" @{
                encoding = 'base64'; content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName))
            }
            $tree.Add(@{ path = $relative; mode = '100644'; type = 'blob'; sha = $blob.sha })
        } else {
            $content = [IO.File]::ReadAllText($file.FullName)
            # 常见 Key 前缀仅做本地防误上传检查，不输出匹配内容。
            if ($content -match '(?:sk-[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})') {
                throw "发现疑似密钥，已停止上传：$relative"
            }
            $tree.Add(@{ path = $relative; mode = '100644'; type = 'blob'; content = $content })
        }
    }
    # 阶段三：新 tree 和 commit 完整创建后再推进分支，不进行 force push。
    $newTree = Invoke-GitHubApi 'POST' "repos/$FullName/git/trees" @{ base_tree = $parent.tree.sha; tree = $tree.ToArray() }
    $commit = Invoke-GitHubApi 'POST' "repos/$FullName/git/commits" @{
        message = 'Publish Fluffy Cat: minimal dropdown and permission-safe voice input'
        tree = $newTree.sha; parents = @($parent.sha)
    }
    $null = Invoke-GitHubApi 'PATCH' "repos/$FullName/git/refs/heads/$Branch" @{ sha = $commit.sha; force = $false }
    return $commit.sha
}

<#
输入：FullName（刚创建的仓库）、Branch（已推送的分支）、BuildMarker（本版页面标识）。
输出：经 HTTPS 200 和内容标识验证的网页地址。
功能：启用 Pages、等待构建；未完成时抛出错误，绝不把猜测的网址当作上线结果。
#>
function Enable-Pages {
    param([string]$FullName, [string]$Branch, [string]$BuildMarker)
    # 阶段一：从实际默认分支的根目录发布，不依赖另一个部署平台或付费后端。
    $null = Invoke-GitHubApi 'POST' "repos/$FullName/pages" @{ build_type = 'legacy'; source = @{ branch = $Branch; path = '/' } }
    $null = Invoke-GitHubApi 'PUT' "repos/$FullName/pages" @{ https_enforced = $true }
    try { $null = Invoke-GitHubApi 'POST' "repos/$FullName/pages/builds" } catch { Write-Host 'Pages 初次构建可能已开始，继续查询状态。' }
    # 阶段二：查询真实构建状态，并独立检验返回的网页是否已更新为本版内容。
    for ($i = 0; $i -lt 100; $i++) {
        Start-Sleep -Seconds 4
        $site = Invoke-GitHubApi 'GET' "repos/$FullName/pages"
        if ($site.status -eq 'errored') { throw "Pages 构建失败，请查看仓库的 Actions：$FullName" }
        Write-Host "  Pages 状态：$($site.status)"
        if ($site.status -ne 'built') { continue }
        $url = [string]$site.html_url
        if (-not $url.StartsWith('https://')) { throw 'GitHub 尚未返回 HTTPS 地址。请稍后在 Pages 设置里检查。' }
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
            if ($response.StatusCode -eq 200 -and $response.Content.Contains($BuildMarker)) { return $url }
        } catch { Write-Host '  站点仍在同步，继续等待。' }
    }
    throw "仓库已上传，但 Pages 尚未验证上线。稍后检查 https://github.com/$FullName/settings/pages 。不要重新创建同名仓库。"
}

try {
    # 阶段一：检查工具、登录账号和待发布源码；此阶段还不会创建仓库。
    Write-Host "`nFluffy Cat - GitHub Pages 发布`n"
    $script:Gh = Find-GitHubCli
    $loggedIn = $false
    try { & $script:Gh auth status --hostname github.com *> $null; $loggedIn = ($LASTEXITCODE -eq 0) } catch { $loggedIn = $false }
    if (-not $loggedIn) {
        & $script:Gh auth login --hostname github.com --web --git-protocol https --skip-ssh-key
        if ($LASTEXITCODE -ne 0) { throw 'GitHub 登录没有完成。' }
    }
    $profile = Invoke-GitHubApi 'GET' 'user'
    if ($profile.login -ine $ExpectedOwner) { throw "当前账号是 $($profile.login)，不是 $ExpectedOwner。请切换正确账号后重试。" }
    $files = @(Get-PublishFiles)
    $fullName = "$($profile.login)/$RepositoryName"
    Write-Host "将新建公开仓库：$fullName"
    Write-Host '源码和猫咪素材会公开。不会上传 API Key、语音或本机记录。'
    if ((Read-Host "输入仓库名 $RepositoryName 确认发布") -cne $RepositoryName) { throw '已取消，没有创建仓库。' }

    # 阶段二：只创建新仓库；同名仓库存在时 POST 会失败，不执行任何覆盖。
    $repository = Invoke-GitHubApi 'POST' 'user/repos' @{
        name = $RepositoryName; private = $false; auto_init = $true
        description = 'Fluffy Cat: a minimal voice-aware workout journal with continuous mascot animation'
    }
    $commit = Push-Source $fullName $files $repository.default_branch
    Write-Host "`n源码已上传：$($repository.html_url)`n等待 Pages 上线…"

    # 阶段三：获得服务器实际返回的地址，验证成功后才打开浏览器。
    $url = Enable-Pages $fullName $repository.default_branch 'fluffy-pages-20260921-mic-v2'
    $result = @{ repository = $repository.html_url; pages = $url; commit = $commit }
    [IO.File]::WriteAllText((Join-Path $script:Root 'deployment-result.json'), (ConvertTo-Json $result), $script:Utf8)
    Write-Host "`n部署成功：$url`n以后直接访问这个地址，不用打开本地 HTML。" -ForegroundColor Green
    Start-Process $url
} catch {
    Write-Host "`n发布未完成：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host '没有验证上线的地址不会显示为部署成功。'
    exit 1
}
