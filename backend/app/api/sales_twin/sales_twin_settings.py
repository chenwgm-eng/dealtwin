"""设置路由 - 公司档案、LLM 配置、产品附件"""
import os
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401
from app.models.database import CompanyProfile, CompanyAttachment
from app.config import Config

# 公司产品附件上传目录
COMPANY_ATTACHMENT_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/company')


def _apply_llm_config(profile):
    """将 CompanyProfile 中的 LLM 配置应用到运行时 Config 类"""
    from app.config import Config
    if profile.llm_api_key:
        Config.LLM_API_KEY = profile.llm_api_key
    if profile.llm_base_url:
        Config.LLM_BASE_URL = profile.llm_base_url
    if profile.llm_model_name:
        Config.LLM_MODEL_NAME = profile.llm_model_name


def _profile_to_dict(profile):
    """公司档案转字典（llm_api_key 脱敏）"""
    return {
        'id': profile.id,
        'company_name': profile.company_name,
        'company_intro': profile.company_intro,
        'product_intro': profile.product_intro,
        'llm_api_key': '已配置' if profile.llm_api_key else None,
        'llm_base_url': profile.llm_base_url,
        'llm_model_name': profile.llm_model_name,
    }


def _attachment_to_dict(att):
    """附件转字典（不含 extracted_text，避免列表接口返回大段文本）"""
    return {
        'id': att.id,
        'file_name': att.file_name,
        'file_type': att.file_type,
        'file_size': att.file_size,
        'uploaded_at': att.uploaded_at.isoformat() if att.uploaded_at else None,
    }


def _extract_text_from_file(file_path, file_type):
    """从文件中提取文本内容

    支持 pdf/md/txt/markdown；提取失败返回空字符串。
    """
    file_type = (file_type or '').lower()
    try:
        if file_type == 'pdf':
            import pdfplumber
            texts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    texts.append(page_text)
            return '\n\n'.join(texts).strip()
        else:
            # md / txt / markdown：直接读取文本
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f'提取文件文本失败 [{file_path}]: {e}')
        return ''


@sales_twin_bp.route('/settings', methods=['GET'])
def get_settings():
    """获取公司档案 + 附件列表"""
    profile = CompanyProfile.query.first()
    attachments = CompanyAttachment.query.order_by(CompanyAttachment.uploaded_at.asc()).all()
    return jsonify({
        'success': True,
        'profile': _profile_to_dict(profile) if profile else None,
        'attachments': [_attachment_to_dict(a) for a in attachments],
    }), 200


@sales_twin_bp.route('/settings', methods=['PUT'])
def update_settings():
    """更新公司档案（company_name、company_intro、product_intro、llm_*）

    - CompanyProfile 不存在则创建（单例）
    - llm_api_key 为空字符串或不传时不覆盖已有值（允许用户不改 key）
    - 保存后调用 _apply_llm_config 更新运行时 Config
    """
    data = request.get_json() or {}

    profile = CompanyProfile.query.first()
    if profile is None:
        profile = CompanyProfile()
        db.session.add(profile)

    if 'company_name' in data:
        profile.company_name = data.get('company_name')
    if 'company_intro' in data:
        profile.company_intro = data.get('company_intro')
    if 'product_intro' in data:
        profile.product_intro = data.get('product_intro')
    if 'llm_base_url' in data:
        profile.llm_base_url = data.get('llm_base_url')
    if 'llm_model_name' in data:
        profile.llm_model_name = data.get('llm_model_name')
    # llm_api_key：仅在传入非空字符串时覆盖（允许用户不改 key）
    new_api_key = data.get('llm_api_key')
    if new_api_key:
        profile.llm_api_key = new_api_key

    db.session.commit()

    # 应用到运行时 Config
    _apply_llm_config(profile)

    attachments = CompanyAttachment.query.order_by(CompanyAttachment.uploaded_at.asc()).all()
    return jsonify({
        'success': True,
        'profile': _profile_to_dict(profile),
        'attachments': [_attachment_to_dict(a) for a in attachments],
    }), 200


@sales_twin_bp.route('/settings/attachments', methods=['POST'])
def upload_company_attachment():
    """上传产品附件（multipart/form-data，字段名 file）

    - 保存到 uploads/company/ 目录
    - 提取文本内容存入 extracted_text 字段
    - 支持 pdf/md/txt/markdown
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '缺少 file 字段'}), 400
    f = request.files['file']
    if not f or not f.filename:
        return jsonify({'success': False, 'error': '未检测到上传文件'}), 400

    original_filename = f.filename
    ext = os.path.splitext(original_filename)[1]
    type_ext = ext.lstrip('.').lower() if ext else ''
    if type_ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'error': f'不支持的文件类型: {type_ext}'}), 400

    # 确保目录存在
    os.makedirs(COMPANY_ATTACHMENT_DIR, exist_ok=True)
    stored_filename = f'{uuid.uuid4().hex}{ext}'
    save_path = os.path.join(COMPANY_ATTACHMENT_DIR, stored_filename)
    f.save(save_path)
    file_size = os.path.getsize(save_path)

    # 提取文本
    extracted_text = _extract_text_from_file(save_path, type_ext)

    attachment = CompanyAttachment(
        file_name=original_filename,
        file_path=stored_filename,
        file_type=type_ext,
        file_size=file_size,
        extracted_text=extracted_text,
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify({
        'success': True,
        'attachment': _attachment_to_dict(attachment),
    }), 200


@sales_twin_bp.route('/settings/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_company_attachment(attachment_id):
    """删除附件记录和文件"""
    attachment = CompanyAttachment.query.get(attachment_id)
    if not attachment:
        return jsonify({'success': False, 'error': '附件不存在'}), 404

    # 删除磁盘文件
    if attachment.file_path:
        full_path = os.path.join(COMPANY_ATTACHMENT_DIR, attachment.file_path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except OSError as e:
            logger.warning(f'删除附件文件失败 [{full_path}]: {e}')

    db.session.delete(attachment)
    db.session.commit()
    return jsonify({'success': True}), 200


@sales_twin_bp.route('/settings/attachments/<int:attachment_id>/download', methods=['GET'])
def download_company_attachment(attachment_id):
    """下载附件文件"""
    attachment = CompanyAttachment.query.get(attachment_id)
    if not attachment:
        return jsonify({'success': False, 'error': '附件不存在'}), 404

    return send_from_directory(
        COMPANY_ATTACHMENT_DIR,
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.file_name,
    ), 200
