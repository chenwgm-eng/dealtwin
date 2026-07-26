"""干系人与关系路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401

# 合法社交风格（Challenger Tailoring）
VALID_SOCIAL_STYLES = ('analytical', 'driver', 'amiable', 'expressive')


@sales_twin_bp.route('/projects/<int:project_id>/stakeholders', methods=['POST'])
def create_stakeholder(project_id):
    """创建干系人"""
    project = get_project_or_404(project_id)
    data = request.get_json()

    required_fields = ['name']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必填字段: {field}'}), 400

    # 社交风格枚举校验（None 表示未识别）
    social_style = data.get('social_style')
    if social_style in ('', 'null'):
        social_style = None
    if social_style is not None and social_style not in VALID_SOCIAL_STYLES:
        return jsonify({'error': f'非法社交风格: {social_style}，可选值: {"/".join(VALID_SOCIAL_STYLES)} 或 null'}), 400

    # 如果关联了客户联系人，自动同步姓名和职位，并尝试带出汇报对象
    name = data['name']
    position = data.get('position')
    contact_id = data.get('contact_id')
    reports_to_id = data.get('reports_to_id')
    contact = None
    if contact_id:
        contact = Contact.query.get(contact_id)
        if contact:
            # 优先使用联系人姓名（除非用户明确输入了新姓名）
            if not name or name.strip() == '':
                name = contact.name
            if not position:
                position = contact.position
            # 自动带出汇报对象：根据 contact.reports_to 在项目干系人中查找
            if not reports_to_id:
                reports_to_id = _resolve_reports_to_from_contact(project_id, contact)

    stakeholder = Stakeholder(
        project_id=project_id,
        name=name,
        position=position,
        level=data.get('level'),
        responsibilities=data.get('responsibilities'),
        personal_agenda=data.get('personal_agenda'),
        buyer_role=data.get('buyer_role'),
        social_style=social_style,
        project_role=data.get('project_role'),
        status=data.get('status', 'confirmed'),  # 手工创建默认已确认
        contact_id=contact_id,
        reports_to_id=reports_to_id,
        decision_power=data.get('decision_power', 5),
        support_level=data.get('support_level', 5),
        urgency=data.get('urgency', 5)
    )

    db.session.add(stakeholder)
    db.session.commit()

    return jsonify({'stakeholder': stakeholder_to_dict(stakeholder)}), 200



@sales_twin_bp.route('/projects/<int:project_id>/stakeholders', methods=['GET'])
def get_stakeholders(project_id):
    """获取项目干系人列表"""
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    # 批量预加载：reports_to_map（干系人 id→姓名）和 contact_map（联系人 id→Contact 对象）
    # 避免 stakeholder_to_dict 内逐条 Stakeholder.query.get / Contact.query.get 产生 N+1
    reports_to_ids = {s.reports_to_id for s in stakeholders if s.reports_to_id}
    contact_ids = {s.contact_id for s in stakeholders if s.contact_id}
    reports_to_map = {
        s.id: s.name for s in Stakeholder.query.filter(Stakeholder.id.in_(reports_to_ids)).all()
    } if reports_to_ids else {}
    contact_map = {}
    if contact_ids:
        # 同时把联系人的 reports_to_id 也纳入查询，以便在 contact_map 内解析 boss 联系人姓名
        contacts = Contact.query.filter(Contact.id.in_(contact_ids)).all()
        boss_ids = {c.reports_to_id for c in contacts if c.reports_to_id}
        if boss_ids:
            existing = {c.id for c in contacts}
            missing = boss_ids - existing
            if missing:
                contacts.extend(Contact.query.filter(Contact.id.in_(missing)).all())
        contact_map = {c.id: c for c in contacts}
    return jsonify({
        'stakeholders': [stakeholder_to_dict(s, reports_to_map=reports_to_map, contact_map=contact_map) for s in stakeholders]
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/stakeholders/contacts', methods=['GET'])
def get_project_stakeholder_contacts(project_id):
    """获取项目关联客户的所有联系人列表（供干系人关联选择）

    返回该项目关联客户的联系人列表，用于在创建/编辑干系人时
    通过姓名模糊匹配选择"关联客户联系人"或"手工输入第三方临时性人员"。
    每个联系人附带 reports_to_id / reports_to_name，供前端在关联时
    自动带出汇报对象。
    """
    project = get_project_or_404(project_id)
    customer_id = getattr(project, 'customer_id', None)
    contacts = []
    if customer_id:
        all_contacts = Contact.query.filter_by(customer_id=customer_id).all()
        # 标识已被关联到该商机干系人的联系人
        linked_ids = {
            s.contact_id for s in Stakeholder.query
            .filter_by(project_id=project_id)
            .filter(Stakeholder.contact_id.isnot(None))
            .all()
        }
        # 预加载所有联系人的 id→对象映射，用于解析 reports_to 名称
        contact_map = {ct.id: ct for ct in all_contacts}
        for ct in all_contacts:
            reports_to_name = None
            if ct.reports_to_id and ct.reports_to_id in contact_map:
                reports_to_name = contact_map[ct.reports_to_id].name
            contacts.append({
                'id': ct.id,
                'name': ct.name,
                'department': ct.department,
                'position': ct.position,
                'phone': ct.phone,
                'email': ct.email,
                'customer_id': ct.customer_id,
                'reports_to_id': ct.reports_to_id,
                'reports_to_name': reports_to_name,
                'linked': ct.id in linked_ids,
            })
    return jsonify({
        'customer_id': customer_id,
        'contacts': contacts,
        'total': len(contacts)
    }), 200



@sales_twin_bp.route('/stakeholders/<int:stakeholder_id>', methods=['PUT'])
def update_stakeholder(stakeholder_id):
    """更新干系人（记录每个字段变更到StateChangeLog）"""
    stakeholder = Stakeholder.query.get_or_404(stakeholder_id)
    data = request.get_json()

    # 字段中文名映射
    field_labels = {
        'name': '姓名',
        'position': '职位',
        'level': '级别',
        'responsibilities': '职责',
        'personal_agenda': '个人诉求',
        'buyer_role': '角色类型',
        'social_style': '社交风格',
        'project_role': '项目角色',
        'status': '状态',
        'contact_id': '关联联系人',
        'reports_to_id': '汇报对象',
        'decision_power': '决策力',
        'support_level': '支持度',
        'urgency': '紧迫感',
    }

    # 社交风格枚举校验（None/空串 表示清除）
    if 'social_style' in data:
        if data['social_style'] is None or data['social_style'] in ('', 'null'):
            data['social_style'] = None
        elif data['social_style'] not in VALID_SOCIAL_STYLES:
            return jsonify({'error': f'非法社交风格: {data["social_style"]}，可选值: {"/".join(VALID_SOCIAL_STYLES)} 或 null'}), 400

    change_logs = []
    reasoning = data.get('edit_reason') or data.get('reasoning') or '手动编辑'

    # 关联联系人变化时，自动带出汇报对象（除非用户显式传入了 reports_to_id）
    if 'contact_id' in data and 'reports_to_id' not in data:
        new_contact_id = data['contact_id']
        if new_contact_id in ('', 0, '0', None):
            new_contact_id = None
        if new_contact_id and new_contact_id != stakeholder.contact_id:
            ct = Contact.query.get(new_contact_id)
            if ct:
                resolved = _resolve_reports_to_from_contact(stakeholder.project_id, ct)
                if resolved:
                    data['reports_to_id'] = resolved

    for field, label in field_labels.items():
        if field not in data:
            continue
        old_val = getattr(stakeholder, field)
        new_val = data[field]
        # 类型转换比较
        if field in ('decision_power', 'support_level', 'urgency'):
            try:
                new_val = int(new_val)
            except (TypeError, ValueError):
                continue
        if field in ('reports_to_id', 'contact_id'):
            # 空字符串/None/0 统一为 None
            if new_val in ('', 0, '0', None):
                new_val = None
            # reports_to_id 不能自己汇报给自己
            if field == 'reports_to_id' and new_val == stakeholder.id:
                continue
        # Enum 字段规范化为字符串比较
        if field in ('buyer_role', 'project_role', 'social_style'):
            old_val = _enum_str(old_val)
            new_val = new_val if new_val in ('', None) else (new_val.value if hasattr(new_val, 'value') else str(new_val))
        if old_val == new_val:
            continue
        # 记录变更日志
        # 对 reports_to_id / contact_id 显示名称而非ID
        def _display_val(val, field_name):
            if field_name == 'reports_to_id' and val:
                boss = Stakeholder.query.get(val)
                return boss.name if boss else str(val)
            if field_name == 'contact_id' and val:
                ct = Contact.query.get(val)
                return ct.name if ct else str(val)
            return str(val) if val is not None else ''

        log = StateChangeLog(
            project_id=stakeholder.project_id,
            stakeholder_id=stakeholder.id,
            change_object=stakeholder.name,
            attribute_name=field,
            old_value=_display_val(old_val, field),
            new_value=_display_val(new_val, field),
            reasoning=reasoning,
            change_source='manual_edit'
        )
        db.session.add(log)
        change_logs.append({
            'field': field,
            'label': label,
            'old': old_val,
            'new': new_val
        })
        setattr(stakeholder, field, new_val)

    stakeholder.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'stakeholder': stakeholder_to_dict(stakeholder),
        'change_logs': change_logs,
        'total_changes': len(change_logs)
    }), 200



@sales_twin_bp.route('/stakeholders/<int:stakeholder_id>', methods=['DELETE'])
def delete_stakeholder(stakeholder_id):
    """删除干系人（仅删除该商机中的干系人记录，不删除关联的客户联系人）"""
    stakeholder = Stakeholder.query.get_or_404(stakeholder_id)
    stakeholder_name = stakeholder.name
    project_id = stakeholder.project_id

    # 解除其他干系人对此干系人的汇报关系（reports_to_id 置空）
    subordinates = Stakeholder.query.filter_by(reports_to_id=stakeholder_id).all()
    for sub in subordinates:
        sub.reports_to_id = None

    # 删除此干系人关联的状态变更日志（避免外键悬空）
    StateChangeLog.query.filter_by(stakeholder_id=stakeholder_id).delete()

    # 其名下的商业指导话术转为通用话术（stakeholder_id 置空，保留内容）
    ChallengerTeaching.query.filter_by(stakeholder_id=stakeholder_id).update({'stakeholder_id': None})

    db.session.delete(stakeholder)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'干系人「{stakeholder_name}」已从项目中移除',
        'stakeholder_id': stakeholder_id,
        'project_id': project_id
    }), 200



def _merge_stakeholder_fields(primary, secondary, override, project_id):
    """合并两个干系人的字段值（空字段填充 + 数值取较高 + override 覆盖）

    Returns:
        merged_fields: list[str] - 已合并字段描述列表
    """
    merged_fields = []

    def _log_field_change(field, old_val, new_val):
        """合并字段变更时记录 StateChangeLog（change_source='manual_edit'）"""
        if old_val == new_val:
            return
        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=primary.id,
            change_object=primary.name,
            attribute_name=field,
            old_value=str(old_val) if old_val is not None else '',
            new_value=str(new_val) if new_val is not None else '',
            reasoning=f'合并干系人 {secondary.name} 的字段',
            change_source='manual_edit'
        )
        db.session.add(log)

    # 对空字段用次记录填充
    fill_fields = ['position', 'level', 'responsibilities', 'personal_agenda',
                   'buyer_role', 'project_role']
    for field in fill_fields:
        primary_val = getattr(primary, field)
        secondary_val = getattr(secondary, field)
        # 优先用override指定的值
        if field in override:
            new_val = override[field]
            if new_val and getattr(primary, field) != new_val:
                _log_field_change(field, primary_val, new_val)
                setattr(primary, field, new_val)
                merged_fields.append(f'{field}(override)')
        elif not primary_val and secondary_val:
            _log_field_change(field, primary_val, secondary_val)
            setattr(primary, field, secondary_val)
            merged_fields.append(f'{field}(from {secondary.name})')

    # 数值字段取较高值（决策力/支持度/紧迫感）— 合并后信息更完整
    for num_field in ['decision_power', 'support_level', 'urgency']:
        if num_field in override:
            try:
                new_val = int(override[num_field])
                if getattr(primary, num_field) != new_val:
                    _log_field_change(num_field, getattr(primary, num_field), new_val)
                    setattr(primary, num_field, new_val)
                    merged_fields.append(f'{num_field}(override)')
            except (TypeError, ValueError):
                pass
        else:
            secondary_val = getattr(secondary, num_field) or 0
            primary_val = getattr(primary, num_field) or 0
            if secondary_val > primary_val:
                _log_field_change(num_field, primary_val, secondary_val)
                setattr(primary, num_field, secondary_val)
                merged_fields.append(f'{num_field}(from {secondary.name})')

    # 汇报对象：如果主记录没有汇报对象，且次记录的汇报对象不是主记录自身，则继承
    if not primary.reports_to_id and secondary.reports_to_id:
        if secondary.reports_to_id != primary.id:
            _log_field_change('reports_to_id', primary.reports_to_id, secondary.reports_to_id)
            primary.reports_to_id = secondary.reports_to_id
            merged_fields.append(f'reports_to_id(from {secondary.name})')

    return merged_fields


def _migrate_stakeholder_associations(primary, secondary):
    """迁移次干系人的关联数据到主干系人（待办/关系/状态日志/reports_to_id/stakeholder_ids）"""
    # 1. 待办事项的 stakeholder_id
    OpportunityTask.query.filter_by(stakeholder_id=secondary.id).update(
        {'stakeholder_id': primary.id}
    )
    # 2. 关系表 source_id / target_id
    Relationship.query.filter_by(source_id=secondary.id).update({'source_id': primary.id})
    Relationship.query.filter_by(target_id=secondary.id).update({'target_id': primary.id})
    # 3. 状态日志 stakeholder_id
    StateChangeLog.query.filter_by(stakeholder_id=secondary.id).update(
        {'stakeholder_id': primary.id}
    )
    # 4. 其他干系人的 reports_to_id 指向次记录的，改为指向主记录
    Stakeholder.query.filter_by(reports_to_id=secondary.id).update(
        {'reports_to_id': primary.id}
    )

    # 5. 合并 OpportunityTask/MeetingPlan 的 stakeholder_ids JSON 数组中的 secondary.id
    for tbl in [OpportunityTask, MeetingPlan]:
        if not hasattr(tbl, 'stakeholder_ids'):
            continue
        items = tbl.query.filter(tbl.stakeholder_ids.contains(str(secondary.id))).all()
        for item in items:
            try:
                ids = json.loads(item.stakeholder_ids) if item.stakeholder_ids else []
            except (json.JSONDecodeError, TypeError):
                ids = []
            if secondary.id in ids:
                ids = [primary.id if x == secondary.id else x for x in ids]
                # 去重
                seen = set()
                deduped = []
                for x in ids:
                    if x not in seen:
                        seen.add(x)
                        deduped.append(x)
                item.stakeholder_ids = json.dumps(deduped, ensure_ascii=False)


@sales_twin_bp.route('/projects/<int:project_id>/stakeholders/merge', methods=['POST'])
def merge_stakeholders(project_id):
    """合并两个干系人（保留主记录，将次记录的信息合并后删除次记录）

    请求体：
    - primary_id: 保留的干系人ID
    - secondary_id: 被合并删除的干系人ID
    - override: 可选，指定哪些字段用次记录的值覆盖主记录 {field: value}
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    primary_id = data.get('primary_id')
    secondary_id = data.get('secondary_id')
    override = data.get('override', {})

    if not primary_id or not secondary_id:
        return jsonify({'error': '需要 primary_id 和 secondary_id'}), 400
    if primary_id == secondary_id:
        return jsonify({'error': '不能与自身合并'}), 400

    primary = Stakeholder.query.get_or_404(primary_id)
    secondary = Stakeholder.query.get_or_404(secondary_id)
    if primary.project_id != project_id or secondary.project_id != project_id:
        return jsonify({'error': '干系人不属于该项目'}), 400

    merged_fields = _merge_stakeholder_fields(primary, secondary, override, project_id)
    _migrate_stakeholder_associations(primary, secondary)

    # 记录合并日志
    log = StateChangeLog(
        project_id=project_id,
        stakeholder_id=primary.id,
        change_object=primary.name,
        attribute_name='merged',
        old_value=secondary.name,
        new_value=primary.name,
        reasoning=f'合并干系人：将 {secondary.name} 合并到 {primary.name}（{"; ".join(merged_fields) if merged_fields else "无字段变更"}）',
        change_source='manual_edit'
    )
    db.session.add(log)

    # 删除次记录
    db.session.delete(secondary)
    primary.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'stakeholder': stakeholder_to_dict(primary),
        'merged_fields': merged_fields,
        'message': f'已将 {secondary.name} 合并到 {primary.name}'
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/relationships', methods=['POST'])
def create_relationship(project_id):
    """创建关系"""
    project = get_project_or_404(project_id)
    data = request.get_json()
    
    required_fields = ['source_id', 'target_id', 'relationship_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必填字段: {field}'}), 400
    
    relationship = Relationship(
        project_id=project_id,
        source_id=data['source_id'],
        target_id=data['target_id'],
        relationship_type=data['relationship_type'],
        influence_weight=data.get('influence_weight', 0.5)
    )
    
    db.session.add(relationship)
    db.session.commit()
    
    return jsonify({'relationship': relationship_to_dict(relationship)}), 200



@sales_twin_bp.route('/projects/<int:project_id>/relationships', methods=['GET'])
def get_relationships(project_id):
    """获取项目关系列表"""
    relationships = Relationship.query.filter_by(project_id=project_id).all()
    return jsonify({'relationships': [relationship_to_dict(r) for r in relationships]}), 200



@sales_twin_bp.route('/relationships/<int:relationship_id>', methods=['PUT'])
def update_relationship(relationship_id):
    """更新关系"""
    relationship = Relationship.query.get_or_404(relationship_id)
    data = request.get_json()
    
    if 'relationship_type' in data:
        relationship.relationship_type = data['relationship_type']
    if 'influence_weight' in data:
        relationship.influence_weight = data['influence_weight']
    
    relationship.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'relationship': relationship_to_dict(relationship)}), 200



@sales_twin_bp.route('/relationships/<int:relationship_id>', methods=['DELETE'])
def delete_relationship(relationship_id):
    """删除关系"""
    relationship = Relationship.query.get_or_404(relationship_id)
    db.session.delete(relationship)
    db.session.commit()
    return jsonify({'success': True, 'message': '关系已删除'}), 200



