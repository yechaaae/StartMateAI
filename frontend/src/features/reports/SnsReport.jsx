import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

export const SnsReport = ({ data }) => <Card><div className="sns-preview"><div><Icon name="play" /><h2>{data.topic}</h2><p>{data.hook}</p></div><section><h3>15초 영상 구성</h3>{data.beats.map((b) => <p key={b}>{b}</p>)}<div className="tags">{data.tags.map((t) => <span key={t}>{t}</span>)}</div><button className="primary-wide"><Icon name="clock" size={16} /> {data.schedule} 게시 예약</button></section></div></Card>
